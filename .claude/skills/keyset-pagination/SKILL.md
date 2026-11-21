---
name: keyset-pagination
description: This skill should be used when the user asks "why is deep pagination slow", "how do I replace OFFSET", "how do I build a cursor-based API", "why do users see duplicate or skipped rows while paging", or is writing a batch job, export, or backfill that pages through a large table.
---

# Keyset pagination

## Why OFFSET fails

```sql
SELECT * FROM events ORDER BY created_at DESC LIMIT 20 OFFSET 200000;
```

The database cannot jump to row 200,000. It must produce and discard 200,000 rows to reach the 20 wanted. Cost is O(offset), so page 10,000 costs 10,000 times page 1.

Two separate failures:

**It slows with depth.** Fine on 500 development rows. A production timeout on deep pages only, affecting crawlers and export scripts.

**It returns wrong results on live data.** Rows inserted and deleted between requests shift the offset:

```
t0: user reads page 1 (rows 1-20)
t1: 3 rows are inserted at the top
t2: user reads page 2 (OFFSET 20) -> rows 18, 19, 20 appear again
```

Users see duplicates and rows silently vanish. Any job paging with OFFSET while writes happen **will skip records**, which is how backfills quietly miss rows.

## Keyset: resume from a value

Carry the sort key of the last row and ask for what follows it.

```sql
-- page 1
SELECT id, created_at, title FROM events
ORDER BY created_at DESC, id DESC
LIMIT 20;

-- page 2, passing the last row's (created_at, id)
SELECT id, created_at, title FROM events
WHERE (created_at, id) < ($1, $2)
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

With an index on `(created_at DESC, id DESC)` this is an index seek to the position plus 20 rows: constant time at any depth, and stable against concurrent inserts because it resumes from a value rather than a position.

### Row-value comparison

`(a, b) < (x, y)` is lexicographic comparison, and Postgres and MySQL 8 turn it directly into an index seek. Write it that way:

```sql
WHERE (created_at, id) < ($1, $2)                          -- correct, one seek
WHERE created_at < $1 OR (created_at = $1 AND id < $2)     -- equivalent, often planned worse
WHERE created_at < $1                                      -- WRONG: skips rows sharing created_at
```

The third form is the bug people ship. When any two rows share a `created_at`, rows are skipped at page boundaries.

**Always append a unique tiebreaker** (the primary key) to both the `ORDER BY` and the comparison. Without a total order, pagination cannot be correct.

## Cursors

Do not expose raw column values, since the sort key may need to change later.

```python
cursor = base64.urlsafe_b64encode(
    json.dumps({"t": last.created_at.isoformat(), "i": last.id}).encode())
```

Sign it (HMAC) so clients cannot forge one, and include the sort field name so a cursor from a different ordering is rejected rather than returning nonsense.

Opacity matters for a second reason: a readable encoding will be constructed by hand and can then never change. See `hyrums-law`.

## Bidirectional paging

Reverse the comparison and sort, then reverse the result in application code:

```sql
SELECT * FROM (
  SELECT id, created_at, title FROM events
  WHERE (created_at, id) > ($1, $2)
  ORDER BY created_at ASC, id ASC
  LIMIT 20
) t ORDER BY created_at DESC, id DESC;
```

To know whether a next page exists without a `COUNT`, fetch `LIMIT 21` and return 20. The 21st row's presence is `hasNextPage`. This is what the GraphQL Relay connection spec encodes.

## What is given up

Keyset pagination cannot jump to an arbitrary page number, because computing where page 500 starts is the O(offset) work being removed.

This is usually acceptable, since infinite scroll and next/previous cover most usage. Where numbered pages are required:

- Offer numbered pages for the first N pages where OFFSET is cheap, and keyset beyond.
- Or paginate over a dense indexed sequential column and jump by value.
- Or precompute page boundaries for a static dataset.

Note also that `COUNT(*)` for a total is a separate expensive query and often the real cost of a list endpoint. Prefer `hasNextPage`, or use an estimate:

```sql
SELECT reltuples::bigint FROM pg_class WHERE relname = 'events';
```

## Batch processing

The same technique, and where it matters most. Anything paging with OFFSET while writes happen will skip rows.

```python
last_id = 0
while True:
    rows = db.query(
        "SELECT id, ... FROM users WHERE id > %s ORDER BY id LIMIT 1000", last_id)
    if not rows: break
    process(rows)
    last_id = rows[-1].id
```

Correct, constant cost per batch, and resumable: persist `last_id` and a crashed job restarts where it stopped. Use this shape for every backfill, export, and migration script. See `expand-contract`.

## Migration checklist

1. Add a unique tiebreaker to the `ORDER BY`
2. Create a composite index matching the full sort order and direction, including `DESC`. See `index-design`
3. Replace `OFFSET` with a row-value comparison on the same tuple
4. Return an opaque signed cursor instead of a page number
5. Use `LIMIT n+1` for `hasNextPage` instead of `COUNT(*)`
6. Confirm with `EXPLAIN ANALYZE` that a deep page reads about `LIMIT` rows. See `query-plans`
