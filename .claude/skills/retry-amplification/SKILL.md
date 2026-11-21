---
name: retry-amplification
description: This skill should be used when the user asks "how should I configure retries", "why is the service still down after we fixed the cause", "where should retries live in the call chain", "what backoff should I use", "how do I shed load", or reports a retry storm, thundering herd, or a system that will not recover after restart. Covers retry-driven overload specifically. For herds caused by cache expiry use `cache-stampede`.
---

# Retry amplification and metastable failure

## The multiplication

Retries compose multiplicatively down a call chain:

```
client -> gateway -> service -> database
  3x   x    3x    x    3x    =  27x load at the database
```

The amplification arrives exactly when the database is least able to serve it. A dependency 20% degraded now receives 27x traffic. This is the standard route from a blip to an outage.

## Metastable failure

A system is in a **metastable failure state** when it stays down after the original trigger is gone, because the failure now sustains itself.

```
1. Trigger: a brief latency spike (deploy, GC pause, cache flush, network blip)
2. Requests time out
3. Clients retry
4. Load rises -> more timeouts -> more retries
5. Trigger disappears. Load stays elevated. System stays down.
```

The defining property: removing the cause does not fix it. Restarting does not fix it, because the retry backlog hits the fresh instance immediately. Teams lose hours restarting things during metastable failures.

The only exit is **reducing load**: block traffic at the edge, let the system drain and stabilize, then ramp back slowly. Put this in the runbook, since knowing it in advance turns a four-hour outage into a fifteen-minute one.

Other self-sustaining loops:

- Cold cache after restart, where the origin cannot serve fast enough to repopulate. See `cache-stampede`
- Connection pool exhausted, where establishing connections consumes the capacity needed to serve
- Queue backlog exceeding every consumer's timeout, so all work is stale on arrival
- GC pressure from queued requests causing longer pauses and more queueing

## Rules

### 1. Retry at one layer only

Every retrying layer multiplies. Choose one, usually the layer closest to the user, which knows whether a retry is still useful and holds the deadline. Lower layers fail fast and report upward.

When multiple layers must retry, each needs a budget, and the total must be reasoned about explicitly rather than emerging from three teams' defaults.

### 2. Use a retry budget, not a retry count

A per-request count bounds nothing in aggregate. A budget does:

> Retries may not exceed 10% of successful requests over a rolling window.

While the dependency is healthy, few requests fail and retries are effectively unlimited. While it is unhealthy, successes drop, the budget collapses, and retries stop automatically. This is how gRPC `retryThrottling` and Finagle work. Where the client library lacks it, a token bucket refilled on success is a few dozen lines.

### 3. Only retry retryable things

| Retry | Never retry |
|---|---|
| Connection refused or reset | 400, 401, 403, 404, 422 |
| 503, 502, 429 honoring `Retry-After` | 500 from a non-idempotent write with unknown outcome |
| Timeouts on idempotent operations | Anything whose deadline has already passed |

A timeout is the hard case, since the outcome is unknown. Retrying a non-idempotent operation after a timeout is how customers get charged twice. Fix with **idempotency keys**: the client generates a unique key per logical operation, the server stores it with the result, and a repeat returns the stored result. Make the operation safe, then retry freely.

### 4. Always jitter

Plain exponential backoff synchronizes clients. Everyone fails at the same moment, waits the same interval, and retries together, producing a distributed metronome aimed at the dependency.

```python
sleep = random.uniform(0, min(cap, base * 2 ** attempt))    # full jitter, the default
sleep = min(cap, random.uniform(base, sleep * 3))           # decorrelated jitter
```

Full jitter is the one to memorize. Apply jitter beyond retries: cron schedules, cache TTLs, health check intervals, reconnect delays, token refreshes. Anything periodic across many hosts will otherwise align.

### 5. Circuit breakers

After a failure threshold, stop calling the dependency for a cooldown, then let one probe through. What this buys is not client latency but **room for the dependency to recover**: a struggling service receiving zero traffic for 30 seconds can finish GC, drain its queue, and warm its cache.

Pair with **bulkheads**: a separate connection and thread pool per dependency, so one slow dependency cannot consume every thread in the process.

### 6. Cancel abandoned work

Propagate deadlines and enforce them. A service processing a request whose client gave up 10 seconds ago is burning the capacity needed to recover. Include the database: pass `statement_timeout` and cancel on context cancellation. See `tail-latency`.

## Load shedding

Retries are the client's half. Shedding is the server's half, and it is what actually prevents metastable collapse.

**Shed at the front door**, before allocating a thread, connection, or database handle. A rejection costing a database round trip is not shedding.

**Shed on queue depth or latency, not CPU.** CPU is a lagging indicator. If a request already waited past its deadline in the accept queue, drop it unprocessed.

**Prioritize what gets shed:**

1. **Shed retries first.** Mark retries with a header and shed them preferentially. A retried request is load already partly served, so shedding it directly cuts amplification. Small change, outsized effect, rarely implemented.
2. Shed background and batch traffic before interactive traffic.
3. Shed by customer tier or request cost where that context exists.

**Return 429 with `Retry-After`**, not 503. That tells a well-behaved client both that it may retry and when, moving retry-rate control to the only party that knows.

## Configuration review

1. How many layers in this path retry? Should be one.
2. Is there a retry budget, or only a per-request count?
3. Is jitter applied to retries, cron, health checks, TTLs, and reconnects?
4. Are non-idempotent operations protected by idempotency keys before being retried?
5. Do deadlines propagate, and does anything cancel on expiry?
6. What is the shed path, and does it cost less than the work path?
7. Does the runbook say "drop load, then ramp" for a stuck-after-recovery system?

Multiply the retry counts along the longest call chain. Above 10 means a latent outage is configured and waiting.
