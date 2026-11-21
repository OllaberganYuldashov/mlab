---
name: start-here
description: This skill should be used when the user asks a broad engineering question that could match several areas, asks "which skill covers this", "what skills are available", "where do I start", or describes a symptom without naming a technique. Routes a symptom to exactly one of the coding-skills skills. Load this only when no single skill clearly matches.
---

# Routing

Each coding skill loads independently, and only when it matches. Use the tables below to select **one** skill by symptom, then invoke that skill directly. Do not load several to compare.

## By symptom

| Symptom | Skill |
|---|---|
| Function is hard to follow, too many branches | `cyclomatic-complexity` |
| A change in one place forces changes elsewhere | `connascence` |
| Unsure which code to refactor first | `code-hotspots` |
| Unsure whether an abstraction, wrapper, or split is worth it | `module-depth` |
| Same condition checked repeatedly, null assertions deep in the code | `parse-dont-validate` |
| Concurrent requests corrupt an invariant the code appears to guard | `isolation-anomalies` |
| Need to change a schema, API, or event format without downtime | `expand-contract` |
| Changing undocumented behavior broke a consumer | `hyrums-law` |
| Benchmark p99 looks too good, or production is worse than the load test | `coordinated-omission` |
| Need a pool size, or latency rose without more traffic | `queueing-and-utilization` |
| p99 is bad while p50 is fine, request fans out to many services | `tail-latency` |
| Throughput drops as servers or threads are added | `universal-scalability-law` |
| Service stays down after the cause is fixed, retry storms | `retry-amplification` |
| Load spikes when a cache key expires, or after a flush | `cache-stampede` |
| Distributing keys across a changing set of nodes | `consistent-hashing` |

## Databases

| Symptom | Skill |
|---|---|
| One query is slow and the plan needs reading | `query-plans` |
| Choosing, ordering, or auditing indexes | `index-design` |
| Table grows despite deletes, autovacuum warnings, slow drift over weeks | `mvcc-and-bloat` |
| Out of connections, or tuning pool size against a database | `connection-pooling` |
| Deep pagination is slow, or a backfill skips rows | `keyset-pagination` |
| Building a job queue, or publishing an event atomically with a write | `database-queues` |
| Choosing a storage engine, or disk far exceeds data size | `write-amplification` |

## Correctness and safety

| Symptom | Skill |
|---|---|
| Money is off by a cent, float comparison, NaN, drifting sums | `floating-point` |
| String length, truncation, normalization, case comparison, emoji | `unicode-pitfalls` |
| Measuring elapsed time, ordering events across machines, time zones, DST | `clocks-and-time` |
| Regex over user input, CPU spike on one request, zip or XML bombs | `algorithmic-complexity-attacks` |
| Private registries, lockfiles, package trust | `dependency-confusion` |
| Judging whether an existing test suite is strong | `mutation-testing` |
| Testing something with no known correct output | `metamorphic-testing` |

## Frequently confused pairs

| Question | Skill |
|---|---|
| Is the p99 number trustworthy? | `coordinated-omission` |
| How do I lower the p99? | `tail-latency` |
| What size should this pool be? | `queueing-and-utilization` |
| Why does more capacity make it slower? | `universal-scalability-law` |
| How many database connections? | `connection-pooling` |
| Why is this query slow? | `query-plans` |
| Which index should exist? | `index-design` |
| Thundering herd from cache expiry | `cache-stampede` |
| Thundering herd from retries | `retry-amplification` |
| Are our tests good? | `mutation-testing` |
| How do I test this at all? | `metamorphic-testing` |

## Selection rules

1. Match on the **symptom**, not on vocabulary in the question. A user saying "thundering herd" may mean either the cache case or the retry case, so identify which one the described situation is.
2. Load **one** skill. Each names the related skills where they genuinely apply, and those can be loaded afterwards if needed.
3. Where no row matches, answer directly rather than loading the closest skill. These skills are specific, and a near-match is worse than none.
