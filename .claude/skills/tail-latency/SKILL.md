---
name: tail-latency
description: This skill should be used when the user asks "why is p99 bad when p50 is fine", "how do I reduce tail latency", "should I use hedged requests", "how do I set timeouts for a fan-out", or when a request touches many services or shards and adding a service made latency worse than that service's own latency. Covers reducing tail latency. For whether the p99 number itself is trustworthy use `coordinated-omission`.
---

# Tail latency

One slow server sets the latency of every request that touches it. At a fan-out of 100, a single server's p99 becomes the whole system's p63.

From Dean and Barroso, *The Tail at Scale* (CACM 2013).

## Amplification math

When a request fans out to n servers and needs all of them, the slowest determines latency. Probability that at least one hits its p99:

> **1 - (1 - p)ⁿ**

| Servers touched | Chance of a p99 event | Chance of a p99.9 event |
|---|---|---|
| 1 | 1% | 0.1% |
| 10 | 9.6% | 1% |
| 50 | 39% | 4.9% |
| **100** | **63%** | 9.5% |
| 500 | 99.3% | 39% |

At fan-out 100, one server's p99 becomes the system's p63. Service-level p99 is then determined by dependencies' p99.9 and p99.99, which usually have no SLO and no measurement.

Two consequences:

1. Improving a dependency's p50 is nearly worthless in a fan-out. Improving its p99.9 is everything.
2. Sequential dependencies compose the same way. Ten services each 1% slow gives roughly a 10% chance of a slow response without any parallel fan-out.

## Sources of tail latency

Rarely "the code is slow". The tail comes from things that happen occasionally:

- Shared resource contention: noisy neighbors, memory bandwidth, shared links
- Background daemons: GC, LSM compaction, log rotation, checkpointing, backups, cron
- Queueing, which is nonlinear. See `queueing-and-utilization`
- Maintenance: index rebuilds, leader elections, rebalancing, cache warming after deploy
- Power management: frequency scaling and C-state transitions after idle
- Retries and timeouts, which are tail events by definition

These cannot be eliminated. Build systems that tolerate slow components the way they tolerate failed ones.

## Tail-tolerant techniques

### Hedged requests

Send the request. If no response by the p95 deadline, send a second copy to another replica, take the first response, cancel the other.

```
send to replica A
wait p95_latency         # e.g. 10ms when p50 is 1ms
if no response: send to replica B
take first response, cancel the loser
```

Only 5% of requests hedge, so this costs about 5% extra load and typically halves p99.9 or better. In Google's benchmark it cut p99.9 from 1,800ms to 74ms at a 2% load increase.

Requires an idempotent operation and working cancellation. Cap the hedge rate globally so a system-wide slowdown does not double load exactly when capacity is scarcest.

### Tied requests

Send to two replicas at once, each told the identity of the other. Whichever starts executing first cancels the other. The duplicate-work window is one network round trip. Better than hedging when queueing dominates, but requires server-side cooperation.

### Micro-partitioning

Keep partitions much smaller than the machine count, for example 20 per machine. Load then moves in small increments without resharding, and a hot partition can be relocated or replicated on its own.

### Selective replication

Detect hot items and add replicas only for those, targeting the actual imbalance instead of scaling everything.

### Latency-induced probation

Track per-replica latency and stop sending traffic to a slow one, while continuing shadow requests to detect recovery. Removing a slow replica often matters more than removing a failed one, since a slow replica keeps accepting work it cannot complete.

### Good-enough responses

Return partial results at the deadline rather than waiting for stragglers. Requires product agreement, so make the decision explicitly and record which responses were partial.

### Deadline propagation

The highest-value item here and the most often missing.

Pass a deadline, not a timeout duration, through the whole call chain. Each service subtracts elapsed time and passes the remainder down. Any service finding the deadline passed fails immediately without doing the work.

```
client: deadline = now + 500ms
  -> service A (450ms left) -> service B (400ms left) -> database (380ms left)
```

Without this, a client that gave up at 500ms leaves five services working for nobody, burning the exact capacity needed to recover. gRPC supports deadlines natively. HTTP has no standard, so use a header carrying an absolute timestamp and enforce it, including cancelling in-flight queries via `statement_timeout` or context cancellation. See `retry-amplification`.

## Anti-patterns

- **Unbounded fan-out.** Latency then grows with the worst percentile of an ever-larger sample. Cap or batch it.
- **N+1 across the network.** 100 sequential 5ms calls is 500ms of pure tail exposure.
- **Timeouts tuned to p50.** A timeout at 3x p50 fires on healthy traffic, converting a slow response into a retry, which adds load. Set timeouts from the tail, then reduce the tail.
- **Retrying without a budget.** A retry is a hedge with worse timing.
- **Measuring only local latency.** In a fan-out, local p99 is the dependencies' p99.9.

## What to measure

- p99.9 and p99.99 of every dependency, not only p99
- Fan-out width per request as a distribution. A median of 5 with a p99 of 400 locates the problem
- Time waiting on the slowest branch versus total time, separating fan-out cost from serial work
- Merged histograms rather than averaged percentiles. See `coordinated-omission`
