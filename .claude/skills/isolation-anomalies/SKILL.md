---
name: isolation-anomalies
description: This skill should be used when the user asks "which isolation level do I need", "why did concurrent requests break this invariant", "should I use SELECT FOR UPDATE", "what is write skew", or reports a bug that only reproduces under concurrent traffic, a lost update from a read-modify-write, or confusion about REPEATABLE READ behavior across databases.
---

# Transaction isolation anomalies

Isolation levels are commonly taught as a ladder of "how much locking". That framing causes real bugs. Levels are defined by **which anomalies they permit**, and two databases can use the same label for different guarantees.

| Label | Actual guarantee |
|---|---|
| Postgres `REPEATABLE READ` | Snapshot isolation |
| MySQL InnoDB `REPEATABLE READ` | Snapshot reads plus next-key locks on writes, a different anomaly set |
| Oracle `SERIALIZABLE` | Snapshot isolation, not serializable |
| Postgres `SERIALIZABLE` | Genuinely serializable (SSI), aborting transactions to stay so |

Never reason from the label. Reason from the anomaly table.

## Anomaly table

| Anomaly | READ COMMITTED | SNAPSHOT / PG REPEATABLE READ | SERIALIZABLE |
|---|---|---|---|
| Dirty read | prevented | prevented | prevented |
| Non-repeatable read | **possible** | prevented | prevented |
| Phantom read | **possible** | prevented | prevented |
| Lost update | **possible** | detected, aborts | prevented |
| **Write skew** | **possible** | **possible** | prevented |

Snapshot isolation prevents everything commonly known about and still permits write skew. That is the anomaly that survives intuition.

## Write skew

Invariant: at least one doctor on call. Both transactions start with 2 on call and run concurrently.

```sql
-- transaction A
BEGIN;
SELECT count(*) FROM doctors WHERE on_call AND shift_id = 42;  -- 2, safe to leave
UPDATE doctors SET on_call = false WHERE id = 1;
COMMIT;

-- transaction B, concurrently
BEGIN;
SELECT count(*) FROM doctors WHERE on_call AND shift_id = 42;  -- also 2
UPDATE doctors SET on_call = false WHERE id = 2;
COMMIT;
```

Both commit. Zero doctors on call. Neither wrote the row the other read, so snapshot isolation sees no write-write conflict.

### Detection recipe

Write skew is possible whenever a transaction:

1. **Reads** a set of rows,
2. **Decides** based on what it read,
3. **Writes** something that would have changed that decision had it been visible.

Treat any read-check-write shape under snapshot isolation as broken until fixed. Common instances: booking without overlap, balance checks across accounts, username availability without a unique index, inventory across warehouses, "only one primary" flags, quota enforcement, seat allocation.

## Fixes in order of preference

### 1. Let a constraint enforce it

Cheapest and most reliable, and independent of isolation level or application code.

```sql
CREATE UNIQUE INDEX ON users (lower(email));

ALTER TABLE bookings ADD EXCLUDE USING gist (room_id WITH =, during WITH &&);
```

If the invariant fits a constraint, stop here.

### 2. Make the write atomic

Read-modify-write in application code is the lost-update anomaly. Push arithmetic into the statement and check the row count:

```sql
UPDATE accounts SET balance = balance - 10 WHERE id = 1 AND balance >= 10;
-- 0 rows means insufficient funds
```

### 3. Materialize the conflict

Lock the rows read, so the conflict becomes visible:

```sql
SELECT count(*) FROM doctors WHERE on_call AND shift_id = 42 FOR UPDATE;
```

Locking a single parent row that represents the invariant is often simpler and faster than locking a set. Take locks in a consistent order across the codebase, or write skew is traded for deadlocks.

### 4. SERIALIZABLE

In Postgres this is Serializable Snapshot Isolation: optimistic, no extra locks, aborting transactions that would violate serializability.

```sql
BEGIN ISOLATION LEVEL SERIALIZABLE;
-- ...
COMMIT;   -- may raise SQLSTATE 40001
```

Every SERIALIZABLE transaction requires a retry loop:

```python
for attempt in range(3):
    try:
        with conn.transaction():
            do_work()
        break
    except SerializationFailure:          # 40001, also 40P01 deadlock_detected
        if attempt == 2: raise
        sleep(random.uniform(0, 0.05 * 2**attempt))
```

The transaction body must be retry-safe, with no side effects outside the database until after commit. This is why SERIALIZABLE fails in practice: not throughput, but a retried transaction that sends the email twice.

## Read Committed pitfalls

Most systems default here, so these appear constantly:

- **Two reads in one transaction can disagree.** A report assembled from several queries can be internally inconsistent.
- **`UPDATE` re-reads.** In Postgres a blocked `UPDATE` re-evaluates its `WHERE` against the newly committed row after the lock releases. The predicate may now be false, so check the row count.
- **`SELECT` then `UPDATE` in application code is always a lost-update risk.** Lock, or make the update conditional and check the row count.

## Optimistic concurrency

For long user-facing edits, hold a version column instead of a lock:

```sql
UPDATE docs SET body = $1, version = version + 1
WHERE id = $2 AND version = $3;
-- 0 rows means a concurrent edit
```

## Guidance

- **Default to READ COMMITTED** with constraints and atomic or conditional updates. This covers most applications.
- **Use SERIALIZABLE** for genuinely multi-row invariants such as accounting, scheduling, and quota, accepting the retry loop.
- **Write the concurrency test.** These bugs never appear in single-threaded tests. Use two threads with a barrier so both reach the read before either writes, then assert the invariant. That test is the only proof a fix works.
- **Name the anomaly in review.** "This is write skew under snapshot isolation" ends the discussion.

Reference: Berenson et al., *A Critique of ANSI SQL Isolation Levels* (1995), which named snapshot isolation and write skew.
