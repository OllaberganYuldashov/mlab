---
name: connection-pooling
description: This skill should be used when the user asks "how many database connections should I use", "why is the database out of connections", "should I use PgBouncer", "what is transaction pooling", "why do prepared statements fail behind a pooler", or is configuring pool size, max_connections, RDS Proxy, or a serverless database workload. Covers database connections specifically. For general pool sizing math use `queueing-and-utilization`.
---

# Connection pooling

## Fewer connections is faster

The counterintuitive result that fixes most database-overload incidents: reducing pool size increases throughput and lowers latency.

A Postgres backend is an OS process. Each connection costs memory, a slot in every internal lock table, and a share of CPU spent context switching and thrashing caches. Past the point where all cores are busy, more connections add contention and nothing else.

The mechanism is queueing. With 500 connections, 500 queries interleave, each taking far longer, all finishing late. With 20, queries run to completion quickly and the rest wait in an orderly line. Same throughput, better latency, no thrashing. Queueing in the pool is cheap. Queueing inside the database is not. See `queueing-and-utilization`.

## Sizing

From the HikariCP documentation, derived from Oracle guidance:

> **connections = (core_count x 2) + effective_spindle_count**

For a modern 8-core server on SSD that is roughly 16 to 20, not 200.

Cross-check with Little's Law: 500 queries/sec at 5ms each needs `500 x 0.005 = 2.5` concurrent connections. A pool of 10 gives 4x headroom. Anything beyond buys nothing.

### Fleet-wide sizing

The trap that produces 2,000-connection databases:

```
50 app instances x 20 connections each = 1,000 connections
```

Each instance is sized sensibly, the fleet is not. Options in order:

1. **Put a pooler in front** (PgBouncer, pgcat, RDS Proxy), so app instances hold cheap pooler connections while the pooler holds few real ones.
2. **Shrink per-instance pools as the fleet grows.** Pool size is a function of fleet size, not a constant.
3. **Raise `max_connections`**, the last resort, which usually makes things worse.

Leave headroom for `superuser_reserved_connections`, monitoring, migrations, and an interactive session. Running at exactly `max_connections` means being unable to log in and fix it.

### Timeouts

- **Acquire timeout shorter than the request timeout**, and short. A request waiting 30s for a connection is one nobody is still waiting for.
- **Fail fast when the pool is exhausted.** A slow error is worse than a fast one. See `retry-amplification`.
- **Set `statement_timeout` server-side**, per role or per transaction. A pool full of runaway queries is the most common exhaustion cause, and a client-side timeout does not stop server-side work.
- **Separate pools per workload** as a bulkhead, so analytics cannot consume every connection the checkout path needs.

## PgBouncer modes

| Mode | Connection returned | Multiplexing | Breaks |
|---|---|---|---|
| **Session** | On client disconnect | Almost none | Nothing, but gains little |
| **Transaction** | On `COMMIT` or `ROLLBACK` | High | Session state, see below |
| **Statement** | After each statement | Highest | Multi-statement transactions entirely |

Transaction pooling is the mode worth using. It is what maps 1,000 app connections onto 20 database connections.

### What transaction pooling breaks

Each transaction may get a different backend, so anything living in the session is unreliable:

| Feature | Status |
|---|---|
| `SET` outside a transaction | Broken, use `SET LOCAL` inside the transaction |
| Session-level advisory locks | Broken, use `pg_advisory_xact_lock` |
| `LISTEN` / `NOTIFY` | Broken, needs a dedicated connection |
| `WITH HOLD` cursors | Broken |
| Temporary tables | Broken across transactions |
| `SET ROLE` for row-level security | Broken unless scoped with `SET LOCAL` |

**Prepared statements** bite hardest, since most drivers use them implicitly:

- PgBouncer 1.21+ supports protocol-level prepared statements in transaction mode. Set `max_prepared_statements > 0`.
- Otherwise disable them in the driver: JDBC `prepareThreshold=0`, asyncpg `statement_cache_size=0`, Npgsql `Max Auto Prepare=0`.
- The symptom is unmistakable: `prepared statement "S_1" already exists`, intermittently under load.

Rule of thumb: anything that survives a `COMMIT` will not survive transaction pooling.

## Serverless and Lambda

Each invocation is a fresh process wanting a connection, concurrency scales instantly, and connections are the scarcest resource. 1,000 concurrent Lambdas will open 1,000 connections and take the database down.

- **An external pooler is mandatory**: RDS Proxy, PgBouncer, or a provider's built-in pooler.
- **Pool size 1 per instance**, relying on the pooler to multiplex.
- **Reserve concurrency** on the function so the maximum is bounded by configuration rather than traffic.
- **Reuse the connection across invocations** by declaring it outside the handler, handling the case where it died during a freeze.
- **HTTP data APIs** sidestep connections entirely and suit spiky workloads.

## Diagnosing

```sql
SELECT state, count(*), max(now() - state_change) AS max_age
FROM pg_stat_activity GROUP BY state ORDER BY count DESC;
```

```sql
SELECT wait_event_type, wait_event, count(*)
FROM pg_stat_activity WHERE wait_event IS NOT NULL
GROUP BY 1,2 ORDER BY count DESC;
```

| Finding | Meaning |
|---|---|
| Many `idle in transaction` | The application holds transactions open across other work. Fix the code, set the timeout. This also blocks vacuum, see `mvcc-and-bloat` |
| Many `idle` | Pools too large. Harmless-looking but costs memory and lock-table slots |
| Many `active` and slow | Genuine saturation, or thrashing from too many connections. Try lowering pool size |
| Clients blocked acquiring | Pool too small, or queries too slow. Check query time before enlarging |
| `wait_event_type = Lock` | Contention, not a pool problem. Look at blocking queries |

In PgBouncer, `SHOW POOLS;` and watch `cl_waiting` and `maxwait`. A persistent `maxwait` above a second means the server-side pool is too small or queries are too slow.

## Checklist

1. Pool size derived from cores and Little's Law
2. Fleet total below `max_connections` with headroom
3. Acquire timeout shorter than request timeout
4. `statement_timeout` and `idle_in_transaction_session_timeout` set server-side
5. Separate pools for interactive and analytics workloads
6. Behind a transaction pooler: prepared statements handled, `SET LOCAL` used, no session advisory locks
7. Alerts on pool wait time and `idle in transaction` age
