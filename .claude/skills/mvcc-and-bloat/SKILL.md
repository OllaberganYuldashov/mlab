---
name: mvcc-and-bloat
description: This skill should be used when the user asks "why is the table growing despite deletes", "why did queries get slower over time", "why is autovacuum not keeping up", "what is transaction ID wraparound", "what is idle in transaction", or reports Postgres table or index bloat, replication slot growth, or vacuum warnings.
---

# MVCC and bloat in Postgres

## How rows are stored

Postgres never updates a row in place. Every `UPDATE` writes a new row version and marks the old one dead. Every `DELETE` only marks dead. Space is reclaimed later by vacuum.

Consequences:

- `UPDATE` costs roughly `INSERT` plus `DELETE`.
- `DELETE` temporarily increases table size and never shrinks anything.
- A constantly updated table grows constantly unless vacuum keeps up.
- Updating one column rewrites the whole row, including the untouched 2KB JSONB blob.
- Every index entry must point at the new version, unless the update is HOT.

This is the mechanism behind most "the database got slow and nothing changed" incidents.

## Measuring bloat

Dead rows not yet reclaimed. The cost is not disk but that every sequential scan reads them and the buffer cache fills with garbage. A 10 GB table that is 70% bloat performs like 10 GB while holding 3 GB of live data.

```sql
SELECT relname, n_live_tup, n_dead_tup,
       round(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
       last_autovacuum, pg_size_pretty(pg_total_relation_size(relid)) AS total
FROM pg_stat_user_tables
WHERE n_dead_tup > 10000
ORDER BY n_dead_tup DESC;
```

Above 20% dead warrants investigation. Above 50% indicates a vacuum problem rather than a table problem. For exact numbers use `pgstattuple`, at the cost of a full scan.

## Removing bloat

| Approach | Lock | Notes |
|---|---|---|
| `VACUUM` | non-blocking | Reclaims space for reuse by this table, does not return it to the OS |
| `VACUUM FULL` | `ACCESS EXCLUSIVE` | Returns space to the OS but blocks everything including `SELECT`, and needs 2x disk. Not for a live table |
| `pg_repack` | brief lock only | Same result as `VACUUM FULL`, online. Use this |
| `REINDEX CONCURRENTLY` | brief lock | For index bloat specifically, PG 12+ |

Index bloat is separate from table bloat and often worse, especially on indexes over frequently updated columns.

## Why autovacuum falls behind

Vacuum can remove a row version only when no transaction can still see it. One old snapshot anywhere blocks cleanup across the whole database.

```sql
SELECT pid, state, now() - xact_start AS xact_age, left(query, 80)
FROM pg_stat_activity
WHERE state <> 'idle' OR state = 'idle in transaction'
ORDER BY xact_start NULLS LAST;
```

Check these four blockers in order:

1. **Long-running transactions.** A two-hour analytics query holds a snapshot for two hours.
2. **`idle in transaction` sessions.** The worst case: a transaction opened, one query run, then nothing. Usually an ORM or connection-handling bug. Set `idle_in_transaction_session_timeout = '60s'`.
3. **Replication slots.** An inactive slot, from a departed replica or a stopped CDC consumer, pins WAL and blocks cleanup indefinitely while quietly filling the disk.
   ```sql
   SELECT slot_name, active,
          pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) AS retained
   FROM pg_replication_slots;
   ```
4. **Prepared transactions** left by an unresolved two-phase commit: `SELECT * FROM pg_prepared_xacts;`

Also check `hot_standby_feedback` on replicas. Enabling it makes replica queries block vacuum on the primary. That is usually desirable, since it prevents query cancellations, but it means a long replica query has primary-side consequences.

## Tuning autovacuum

Defaults are conservative and predate fast disks. On a busy table:

```sql
ALTER TABLE high_churn SET (
  autovacuum_vacuum_scale_factor = 0.01,   -- default 0.2 waits for 20% dead
  autovacuum_vacuum_cost_delay = 2,
  autovacuum_vacuum_cost_limit = 1000      -- default 200 is too low to finish
);
```

The scale factor matters most. At 0.2, a 100M-row table waits for 20M dead rows, by which point the vacuum is enormous and slow. Set a low scale factor or a flat `autovacuum_vacuum_threshold` on large tables. Cost limits matter more than `autovacuum_max_workers`, since throttled workers will not keep up regardless of count.

## HOT updates

A Heap-Only Tuple update keeps the new version on the same page and skips index updates entirely. It requires no indexed column to have changed, and free space on the same page.

```sql
SELECT relname, n_tup_upd, n_tup_hot_upd,
       round(100.0 * n_tup_hot_upd / NULLIF(n_tup_upd, 0), 1) AS hot_pct
FROM pg_stat_user_tables WHERE n_tup_upd > 1000 ORDER BY n_tup_upd DESC;
```

To raise the ratio:

- **Do not index frequently changing columns.** An index on `last_seen_at` or `updated_at` disables HOT for every update. Index audits usually miss this cost. See `index-design`.
- **Leave page headroom**: `ALTER TABLE t SET (fillfactor = 85);` then `pg_repack` to apply.

## Transaction ID wraparound

Transaction IDs are 32-bit. Old rows must be frozen by vacuum, or the database eventually **refuses all writes** to protect itself.

```sql
SELECT datname, age(datfrozenxid),
       round(100.0 * age(datfrozenxid) / 2000000000, 1) AS pct_to_wraparound
FROM pg_database ORDER BY age(datfrozenxid) DESC;
```

Alert at 50%, which still leaves time. Past the shutdown threshold, recovery means single-user mode and an outage measured in hours.

An anti-wraparound autovacuum cannot be skipped and will not yield to the workload, so one starting on a huge cold table at peak hour is noticeable. The root cause is almost always the blocker list above, so treat wraparound risk as a symptom.

## Table design for churn

- **Split hot columns out.** A `users` table with `last_seen_at` updated per request rewrites the whole row every time. Move volatile counters to a narrow side table.
- **Partition by time when expiring by time.** Dropping a partition is instant and creates no bloat, while `DELETE FROM events WHERE created_at < ...` creates bloat equal to everything deleted.
- **Give queue tables aggressive per-table settings**, or keep them out of the main database. See `database-queues`.
- **Batch large updates** and vacuum between batches.

## Monitoring checklist

1. `n_dead_tup` and dead percentage per table
2. Oldest transaction age, alerting above a few minutes
3. `idle in transaction` count and age
4. Replication slot retained WAL, alerting on inactive slots
5. `age(datfrozenxid)` as a percentage of the wraparound limit
6. Time since `last_autovacuum` on the busiest tables
7. HOT update ratio on high-churn tables
