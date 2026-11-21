---
name: database-queues
description: This skill should be used when the user asks "how do I build a job queue in Postgres", "what is SELECT FOR UPDATE SKIP LOCKED", "why are jobs processed twice", "how do I publish an event and commit a row atomically", "what is the outbox pattern", or reports workers blocking each other polling a jobs table.
---

# Queues in the database

## Part 1: SKIP LOCKED job queues

A naive jobs table fails with a second worker: workers lock the same oldest row and serialize, or all claim the same job.

`FOR UPDATE SKIP LOCKED` (Postgres 9.5+, MySQL 8+) fixes it by skipping rows already locked by another transaction rather than waiting.

```sql
BEGIN;

WITH claimed AS (
  SELECT id FROM jobs
  WHERE status = 'pending' AND run_at <= now()
  ORDER BY priority DESC, run_at
  FOR UPDATE SKIP LOCKED
  LIMIT 10
)
UPDATE jobs SET status = 'running', started_at = now(), attempts = attempts + 1
FROM claimed WHERE jobs.id = claimed.id
RETURNING jobs.*;

-- process the jobs

COMMIT;
```

Properties:

- Exactly one worker claims each job, guaranteed by row locks.
- Workers never block each other, which is what `SKIP LOCKED` buys.
- A crashed worker's transaction rolls back and its jobs return to `pending` automatically. Committing the claim before processing instead requires a reaper for stuck rows.
- The job and the business data commit together, which is the main reason to keep the queue in the database.

### The index

```sql
CREATE INDEX ON jobs (priority DESC, run_at) WHERE status = 'pending';
```

Partial, because in a healthy queue 99.9% of rows are `done` and a full index would be dead weight. See `index-design`.

### Bloat is the real operational cost

A queue table is the highest-churn table in the system: every job inserted, updated two or three times, then deleted. Under default autovacuum settings it bloats and claim latency creeps up over weeks.

```sql
ALTER TABLE jobs SET (
  autovacuum_vacuum_scale_factor = 0.01,
  autovacuum_vacuum_cost_delay = 0,
  fillfactor = 70                        -- room for HOT updates
);
```

Delete completed jobs promptly, moving them to an archive table or dropping a partition. A jobs table retaining history is a bloat generator. See `mvcc-and-bloat`.

### Operational details

- **Do not poll tightly.** Poll about once a second with jitter, or use `LISTEN`/`NOTIFY` to wake workers with polling as fallback. `LISTEN` needs a dedicated connection and does not work through a transaction pooler, see `connection-pooling`.
- **Batch the claim** to amortize round trips, but only when a worker can process the whole batch within its visibility window.
- **Add a reaper** when committing the claim before processing:
  ```sql
  UPDATE jobs SET status = 'pending'
  WHERE status = 'running' AND started_at < now() - interval '10 minutes';
  ```
- **Cap attempts and use a dead-letter status.** A job failing forever at full speed is a self-inflicted denial of service. Back off exponentially with jitter, see `retry-amplification`.
- **Make handlers idempotent.** At-least-once is the guarantee, since a worker can die after doing the work and before committing.

### When to use a broker instead

A database queue is the right default to roughly thousands of jobs per second: one less system, and transactional consistency with the data, which SQS and Kafka cannot provide. Move to a broker for fan-out to many independent consumers, very high throughput, long retention and replay, or cross-datacenter delivery.

Existing implementations: `pgmq`, River (Go), Oban (Elixir), Solid Queue (Rails), `graphile-worker` (Node), Procrastinate (Python).

## Part 2: the dual-write problem

```python
db.commit()                      # 1. save the order
queue.publish(OrderCreated(...)) # 2. tell everyone
```

These cannot be made atomic. Three real failure modes:

- Crash between 1 and 2: the order exists and nobody hears about it, causing silent divergence.
- Publish succeeds, transaction rolls back: consumers act on an order that does not exist.
- Publish succeeds, commit fails on retry: duplicate events.

Reversing the order does not help. Two-phase commit introduces its own blocking failure mode and most brokers do not support it.

### Transactional outbox

Write the event to the same database in the same transaction, and relay it separately.

```sql
CREATE TABLE outbox (
  id           bigserial PRIMARY KEY,
  aggregate_id text        NOT NULL,
  event_type   text        NOT NULL,
  payload      jsonb       NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  published_at timestamptz
);
CREATE INDEX ON outbox (id) WHERE published_at IS NULL;
```

```python
with db.transaction():
    db.insert(order)
    db.insert_outbox(event_type="OrderCreated", payload=..., aggregate_id=order.id)
# both rows or neither
```

The relay uses the same `SKIP LOCKED` pattern:

```sql
BEGIN;
SELECT * FROM outbox WHERE published_at IS NULL
ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 100;
-- publish to the broker
UPDATE outbox SET published_at = now() WHERE id = ANY($1);
COMMIT;
```

What this guarantees and does not:

- **Guaranteed**: if the order exists, the event is eventually published. Atomicity restored.
- **Not guaranteed**: exactly-once delivery. A relay crashing after publishing but before the `UPDATE` publishes twice. **Consumers must be idempotent**, deduplicating on event id. At-least-once plus idempotent consumers is the achievable target, exactly-once delivery is not.
- **Ordering** is per-aggregate at best. Publish in `id` order and partition the broker by `aggregate_id` when consumers need per-entity ordering.

### CDC as the relay

Debezium reads the Postgres WAL and publishes changes, removing polling load. Costs: another system, and an inactive replication slot pins WAL and fills the disk, see `mvcc-and-bloat`. Polling the outbox is simpler and adequate for most systems.

### The inbox

The mirror image on the consumer side, which is what makes idempotency concrete:

```sql
INSERT INTO processed_events (event_id) VALUES ($1);   -- unique violation means already handled
```

Same transaction as the side effect, so doing the work and recording it cannot diverge. Prune rows on a window longer than the broker's maximum redelivery period.

Delete or partition published outbox rows on a schedule, since the table otherwise grows forever.
