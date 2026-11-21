---
name: expand-contract
description: This skill should be used when the user asks to "rename a column without downtime", "drop a column safely", "add NOT NULL to a live table", "add an index in production", "change an API response shape", "change an event format", or asks how to run a zero-downtime migration. Provides the expand-migrate-contract sequence and per-operation recipes.
---

# Expand and contract

During any rolling deploy, blue-green cutover, or canary, old and new code run simultaneously against the same database, often for minutes and after a rollback for hours.

> Every intermediate state must be compatible with both the old and the new version.

A migration correct only after every process restarts causes an outage. This makes `ALTER TABLE ... RENAME COLUMN` unsafe regardless of how fast it runs: the moment it commits, running old code breaks.

## Three phases

1. **Expand**: add the new thing. Additive only. Old code untouched and unaware.
2. **Migrate**: write to both, backfill, move readers to the new thing, stop writing the old.
3. **Contract**: delete the old thing once nothing reads or writes it.

Each phase is at least one deploy, independently deployable and revertible. The gap between phases is where problems surface, so do not compress it.

## Schema recipes

### Rename a column: six steps

| # | Step | Type |
|---|---|---|
| 1 | `ADD COLUMN new_name` nullable, no rewriting default | schema |
| 2 | Write both columns on every insert and update | code |
| 3 | Backfill `new_name` from `old_name` in batches | script |
| 4 | Read from `new_name`, keep writing both | code |
| 5 | Stop writing `old_name` | code |
| 6 | `DROP COLUMN old_name` | schema |

Stopping between any two steps leaves a correct system. Wait between steps 4 and 6 long enough to be confident there will be no rollback.

### Add a NOT NULL column

```sql
ALTER TABLE users ADD COLUMN plan text;                    -- 1. nullable, instant on PG 11+

-- 2. code writes it on every new row

UPDATE users SET plan = 'free' WHERE plan IS NULL AND id BETWEEN $1 AND $2;   -- 3. batched

ALTER TABLE users ADD CONSTRAINT users_plan_nn CHECK (plan IS NOT NULL) NOT VALID;  -- 4
ALTER TABLE users VALIDATE CONSTRAINT users_plan_nn;       -- takes only SHARE UPDATE EXCLUSIVE
ALTER TABLE users ALTER COLUMN plan SET NOT NULL;          -- PG 12+ uses the constraint, no scan
```

### Other operations

| Change | Safe approach |
|---|---|
| Add an index | `CREATE INDEX CONCURRENTLY` in Postgres (cannot run inside a transaction), online DDL in MySQL 8, or `gh-ost` |
| Change a column type | Treat as a rename: new column, dual-write, backfill, switch, drop |
| Add a foreign key | `ADD CONSTRAINT ... NOT VALID`, then `VALIDATE CONSTRAINT` separately |
| Drop a column | Stop reading (deploy), stop writing (deploy), then drop. Remove it from any `SELECT *` path first |
| Split a table | Dual-write both shapes, backfill, migrate readers, stop writing the old |
| Add a volatile default | Add nullable, backfill in batches, then set the default for new rows |

### The lock queue trap

In Postgres a DDL statement waiting for a lock blocks every query arriving behind it, including plain `SELECT`s. One slow `ALTER` behind one long transaction stalls the whole table. Always cap the wait:

```sql
SET lock_timeout = '3s';
ALTER TABLE ...;   -- fails fast instead of building a queue
```

### Backfills

- Batch a few thousand rows per statement with a pause between batches.
- Never hold one long transaction: it blocks vacuum and grows replication lag. See `mvcc-and-bloat`.
- Make the loop resumable and idempotent by tracking the last id processed. See `keyset-pagination`.
- Throttle on replica lag rather than wall-clock time.

## API and event changes

| Change | Safe approach |
|---|---|
| Add a field | Add it. Consumers must ignore unknown fields, and the contract must say so |
| Rename a field | Emit both, wait for consumers, remove the old |
| Remove a field | Instrument first, deprecate, then remove |
| Change a field's type | New field with a new name. Never change a type in place |
| Change semantics | New field. Repurposing a name is the worst option because nothing breaks loudly, it breaks quietly and wrongly |
| Tighten validation | Log what would have been rejected for a full cycle before rejecting |

Never repurpose a name. A field whose meaning changed is undetectable to consumers, while a field that disappeared is a clear error. Prefer the loud failure.

For queues, add one constraint: a queue holds messages written by the previous version for its full retention window. Consumers must handle both shapes until that window passes after the last old producer stops.

## Instrument before deleting

Prove nothing uses the old thing:

- API field: count reads per field, tagged by client, over a full business cycle including monthly and quarterly jobs
- Column: check query logs and grep every repository, not only this one
- Endpoint: metrics by caller identity, not total request count

"Nobody uses it" without a metric means "nobody I asked". Batch jobs appear at month end, right after the column is dropped. See `hyrums-law`.

## Tools

| Tool | Purpose |
|---|---|
| `squawk` | Lints Postgres migration SQL for unsafe operations |
| `strong_migrations` | Rails gem blocking unsafe migrations and printing the safe recipe |
| `gh-ost`, `pt-online-schema-change` | Online schema change for MySQL |
| `atlas`, `sqldef` | Declarative schema with migration linting |

## Consumer habits that lower the cost

- Never `SELECT *` in application code, since a new column changes the result shape.
- Never rely on column order or JSON key order.
- Be a tolerant reader: ignore unknown fields. Strict validation belongs on fields actually used, not on the whole payload.
- Keep migrations in the repository with the code that needs them.
