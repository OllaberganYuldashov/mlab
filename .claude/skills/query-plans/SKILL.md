---
name: query-plans
description: This skill should be used when the user asks "why is this query slow", "read this EXPLAIN output", "why is the planner not using my index", "why is it fast in staging but slow in production", or shares an execution plan to interpret. Covers EXPLAIN ANALYZE, estimate-versus-actual rows, join strategies, and statistics problems. Covers diagnosing a plan. For choosing which indexes to create use `index-design`.
---

# Reading query plans

## Run it correctly

```sql
EXPLAIN (ANALYZE, BUFFERS, SETTINGS, FORMAT TEXT) SELECT ...;
```

- `ANALYZE` executes the query. For `UPDATE` or `DELETE`, wrap it in a transaction and roll back.
- `BUFFERS` is the commonly omitted flag that matters most: it shows how much data was actually touched.
- `SETTINGS` shows non-default planner parameters, which explains environment differences.

```sql
BEGIN;
EXPLAIN (ANALYZE, BUFFERS) UPDATE ...;
ROLLBACK;
```

## Start with estimate versus actual

```
Seq Scan on orders  (cost=0.00..18584.00 rows=12 width=64) (actual time=0.02..842.11 rows=486213 loops=1)
                                          ^ planner expected 12                       ^ reality: 486,213
```

A plan is a set of decisions built on estimates. When an estimate is off by 40,000x, every decision above it in the tree rests on a wrong assumption: join strategy, memory allocation, index choice. Fixing the estimate usually fixes the query without touching the SQL.

Read the plan bottom-up and find the **deepest node where estimate and actual differ by more than about 10x**. That node is the root cause. Everything above it is a symptom.

### Fixing bad estimates

| Cause | Fix |
|---|---|
| Stale statistics | `ANALYZE tablename;`. Check `last_analyze` in `pg_stat_user_tables` |
| Correlated columns, since the planner assumes independence and multiplies selectivities | `CREATE STATISTICS ... (dependencies, ndistinct) ON city, postcode FROM addresses; ANALYZE;` |
| Skewed distribution | `ALTER TABLE t ALTER COLUMN c SET STATISTICS 1000; ANALYZE;` |
| Expression the planner cannot estimate, such as `WHERE lower(email) = ...` | Create the matching expression index, which also creates statistics for it |
| Join on a computed or cast value | Fix the types so the join is on plain columns |
| Large table never analyzed after a bulk load | Run `ANALYZE` explicitly |

## Node types

### Scans

| Node | Meaning | Warning sign |
|---|---|---|
| `Seq Scan` | Full table read | Large table with a selective filter. Correct when returning more than 5-10% of rows |
| `Index Scan` | Walk the index, fetch each row from the heap | High `loops` |
| `Index Only Scan` | Answered from the index alone | Check `Heap Fetches:`. A high count means visibility-map misses, fixed by `VACUUM` |
| `Bitmap Heap Scan` | Collect pages, then read in physical order | `Rows Removed by Index Recheck` means the bitmap went lossy, so `work_mem` is too small |

### Joins

| Node | Good for | Warning sign |
|---|---|---|
| `Nested Loop` | Small outer input, indexed inner side | **`loops=` in the thousands.** A nested loop chosen because the planner expected 5 outer rows and got 50,000 is the most common cause of a query that became 1000x slower |
| `Hash Join` | Large unsorted inputs | `Batches:` above 1 means the hash spilled to disk, so raise `work_mem` |
| `Merge Join` | Both sides already sorted | A feeding `Sort` that spills to disk |

**Multiply times inside a nested loop.** `actual time=0.03..0.04 rows=1 loops=48000` is roughly 48,000 x 0.04 = 2 seconds, not 0.04ms. Postgres reports per-loop averages for time and rows, while `Buffers` is cumulative. Misreading this is extremely common.

### Other nodes

- `Sort`: check `Sort Method:`. `quicksort Memory: 24kB` is fine, `external merge Disk: 51232kB` means raise `work_mem` for this query.
- `Memoize`: caches inner results and can rescue a nested loop when the hit rate is good.
- `Gather`: compare `Workers Planned` to `Workers Launched`. Fewer launched means hitting `max_parallel_workers`.
- `SubPlan` executed per row: usually a correlated subquery that should be a join or lateral.

## Findings and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `Seq Scan` with a selective `WHERE` | Non-sargable predicate | See `index-design` |
| Nested loop with huge `loops` | Underestimated outer rows | Fix statistics, the join method corrects itself |
| Large `Rows Removed by Filter:` | Index found rows the filter discarded | Add the filtered column to the index, or make it partial |
| High `Heap Fetches:` | Visibility map stale | `VACUUM` the table. See `mvcc-and-bloat` |
| Sort or hash spilling to disk | `work_mem` too low | `SET LOCAL work_mem = '64MB'` per query, since it is per-node and a global raise multiplies across connections |
| Buffers huge relative to rows returned | Table bloat, or a low-selectivity index | Check bloat, reconsider the index |
| Plan looks fine but the query is slow | Time is elsewhere | Check `Planning Time`, lock waits, or network round trips |

## Planning time versus execution time

```
Planning Time: 340.221 ms
Execution Time: 2.108 ms
```

Planning dominating means the query itself is fine. Causes: many partitions, very many indexes, a huge `IN` list, or deeply nested views. Fixes: prepared statements so a generic plan is reused, fewer partitions, simpler views.

## Workflow

1. Run `EXPLAIN (ANALYZE, BUFFERS)`.
2. Find the deepest node where actual greatly exceeds estimate.
3. If the estimate is bad, fix statistics first and re-run before changing anything else. Roughly half of slow-query reports end here.
4. If estimates are good and the node is genuinely expensive, the plan is right and the query or schema is the problem.
5. Verify by comparing **buffers**, not wall-clock time, which is contaminated by cache warmth.

## Tools

- **explain.depesz.com**: colors nodes by estimate error, the fastest way to find the culprit
- **explain.dalibo.com**: plan tree visualization with per-node cost share
- `auto_explain`: logs plans for slow queries in production, the only way to see the plan for the query that was actually slow. Set `auto_explain.log_min_duration = '500ms'`, and sample `log_analyze` since it adds overhead
- `pg_stat_statements`: ranks queries by **total** time, which usually surfaces a fast query called constantly rather than the slow one somebody noticed
