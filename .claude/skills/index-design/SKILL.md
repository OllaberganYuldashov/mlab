---
name: index-design
description: This skill should be used when the user asks "why is my index not being used", "which columns should I index", "what order should the composite index columns be in", "should this be a covering index", "which indexes can I drop", or is choosing a primary key type or auditing unused and duplicate indexes. Covers designing and auditing indexes. For diagnosing a specific slow query use `query-plans`.
---

# Index design

## Composite column order

The most consequential decision and the most often wrong.

A B-tree on `(a, b, c)` is sorted by `a`, then `b` within equal `a`, then `c`. This gives the **leftmost prefix rule**: the index serves `WHERE a = ?`, `WHERE a = ? AND b = ?`, and all three columns, but **not** `WHERE b = ?` alone.

> Equality columns first, then the range or sort column, then the rest.

Once a range predicate (`>`, `<`, `BETWEEN`, `LIKE 'x%'`) is used on a column, every later column in the index can only filter, not seek.

```sql
SELECT * FROM events
WHERE tenant_id = 42 AND created_at > now() - interval '7 days'
ORDER BY created_at DESC;
```

```sql
CREATE INDEX ON events (tenant_id, created_at DESC);   -- equality, then range and sort
```

`(created_at, tenant_id)` forces a scan of a week of all tenants before filtering. The difference is routinely 100x. That the index also satisfies the `ORDER BY` removes a sort node, which is often most of the cost.

**The "most selective column first" rule is usually wrong.** Which columns are used with equality matters far more than cardinality. A low-cardinality `status` belongs first when every query filters `status = 'active'` and ranges on a date. Order by access pattern.

Prefer a small number of well-ordered composites over many single-column indexes. Postgres can combine single-column indexes with a bitmap AND, but that is much slower than one matching composite.

## Sargability

Sargable means the predicate can become an index seek. Wrapping the indexed column in anything usually breaks it.

| Not sargable | Sargable |
|---|---|
| `WHERE lower(email) = 'a@b.c'` | `CREATE INDEX ON users (lower(email))` |
| `WHERE date(created_at) = '2026-01-01'` | `WHERE created_at >= '2026-01-01' AND created_at < '2026-01-02'` |
| `WHERE created_at + interval '1 day' > now()` | `WHERE created_at > now() - interval '1 day'` |
| `WHERE amount * 100 > 5000` | `WHERE amount > 50` |
| `WHERE name LIKE '%smith'` | Trigram index (`pg_trgm`), or store a reversed column |
| `WHERE user_id::text = $1` | Fix the parameter type, since a cast on the column blocks the index |

The type-mismatch case is the sneakiest: a `bigint` column compared to a string parameter silently disables the index, and the plan shows a sequential scan with no explanation.

`OR` across different columns also usually prevents a single seek. Rewrite `WHERE a = 1 OR b = 2` as a `UNION` of two indexed queries.

## Index-only scans and covering indexes

When every column a query needs is in the index, the table is never touched. For columns needed only in output, not for filtering or ordering, use `INCLUDE`, which stores them in leaf pages only:

```sql
CREATE INDEX ON events (tenant_id, created_at) INCLUDE (status, payload_id);
```

Postgres index-only scans still consult the visibility map. An unvacuumed table shows high `Heap Fetches:` and loses most of the benefit. See `mvcc-and-bloat`.

## Partial indexes

Index only the queried rows: smaller index, cheaper writes, better selectivity.

```sql
CREATE INDEX ON jobs (created_at) WHERE status = 'pending';
CREATE INDEX ON users (email) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX ON users (email) WHERE deleted_at IS NULL;
```

The planner uses a partial index only when the query's `WHERE` provably implies the index predicate, so the query must contain a compatible condition. The last example is how to keep real uniqueness alongside soft deletes.

## Primary keys and index locality

A B-tree stays cheap when inserts land at the right-hand edge, since that page stays in memory and fills sequentially.

Random UUIDv4 primary keys destroy that:

- Each insert touches a random cold page, so random I/O replaces sequential
- Pages split at about 50% fill rather than 90%, roughly doubling index size
- The working set becomes the whole index instead of its right edge
- Every secondary index referencing the primary key inherits the bloat

Use time-ordered identifiers: UUIDv7 (RFC 9562) or ULID keep decentralized generation while restoring locality. Postgres 18 ships `uuidv7()`. Existing UUIDv4 keys rarely justify a migration on their own, but get new tables right.

## Auditing

```sql
-- never-used indexes
SELECT relname, indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE idx_scan = 0 AND indexrelid NOT IN (SELECT conindid FROM pg_constraint)
ORDER BY pg_relation_size(indexrelid) DESC;
```

Run this against replicas as well, over a full business cycle, since monthly and quarterly jobs use indexes nothing else touches.

```sql
-- tables taking expensive sequential scans
SELECT relname, seq_scan, seq_tup_read, seq_tup_read / NULLIF(seq_scan,0) AS avg_rows
FROM pg_stat_user_tables WHERE seq_scan > 0 ORDER BY seq_tup_read DESC LIMIT 20;
```

An index on `(a)` is redundant when `(a, b)` exists. Drop the prefix. Use `hypopg` to test a hypothetical index without building it.

## Costs

Every index slows writes and consumes disk. An `INSERT` updates every index. An `UPDATE` updates every index whose columns changed, plus all indexes when the update cannot be HOT.

- Budget roughly 5 indexes per table and justify each beyond that.
- On write-heavy tables, every index must have a named query.
- Build with `CREATE INDEX CONCURRENTLY`, which cannot run in a transaction and leaves an `INVALID` index to drop if it fails.
- Build indexes after bulk loads, not before.

## Non-B-tree types

| Type | Use for |
|---|---|
| **GIN** | Array containment, `jsonb @>`, full-text search, trigram search |
| **GiST** | Ranges, geometry, exclusion constraints such as non-overlapping bookings |
| **BRIN** | Very large naturally-ordered tables such as append-only time series. Tiny index, coarse filtering |
| **Hash** | Equality only, rarely worth it over B-tree |

BRIN is the underused one: on an append-only events table a BRIN index on `created_at` can be kilobytes where a B-tree would be gigabytes.

Verify every index decision with `query-plans`. An index that exists but never appears in a plan is pure write overhead.
