---
name: queueing-and-utilization
description: This skill should be used when the user asks "how big should this thread pool be", "what CPU target is safe", "why did latency spike without more traffic", "do we have headroom at 85% CPU", "how deep should this queue be", or asks to size a worker fleet, connection pool, or WIP limit. Covers sizing and utilization targets. For throughput that drops as workers are added use `universal-scalability-law`, and for database connections use `connection-pooling`.
---

# Queueing and utilization

Two formulas answer most capacity questions.

## Little's Law

> **L = λW**, concurrency = arrival rate x time in system

It holds for any stable system regardless of arrival distribution, service distribution, or scheduling order. That generality is what makes it useful.

| Question | Formula | Example |
|---|---|---|
| Pool size | L = λW | 500 req/s x 40ms = **20 concurrent**, not 200 |
| Latency from queue depth | W = L/λ | 3,000 messages draining at 100/s = **30s behind** |
| Max throughput | λ = L/W | 20 connections at 40ms = **500 q/s ceiling** |
| Time to drain | backlog / (rate - arrival) | 3,000 msgs, 100/s capacity, 60/s arriving = **75s** |

Two habits worth building:

**Sanity-check benchmarks.** A load test claiming 10,000 req/s at 100ms latency with 50 threads implies 1,000 concurrent requests, which 50 threads cannot produce. One of the three numbers is wrong. This catches misconfigured harnesses and coordinated omission immediately. See `coordinated-omission`.

**Size pools from the formula.** Pools are usually set to a round number someone liked. `λ x W` gives an actual answer, almost always smaller than the current setting.

## The utilization curve

For a single-server queue (M/M/1) with utilization ρ:

> **W = S / (1 - ρ)**, wait time = service time / idle fraction

| Utilization | Latency multiplier |
|---|---|
| 50% | 2x |
| 70% | 3.3x |
| **80%** | **5x**, the usual knee |
| 90% | 10x |
| 95% | 20x |
| 99% | 100x |

The curve is a hyperbola, so damage concentrates at the end. Moving from 50% to 60% costs 25% more latency. Moving from 90% to 95% doubles it.

Three conclusions follow:

**"CPU is at 85%, we have headroom" is wrong.** That is throughput headroom with no latency headroom. The remaining 15% of capacity costs 5x to 20x on response time.

**Autoscaling at 80% CPU is too late.** Latency has already tripled by the time the metric trips, and new instances take time to warm. Scale on a lower threshold, or on latency or queue depth directly.

**Check per-shard utilization, not the average.** A 40% fleet average with one node at 95% is a broken system with a healthy dashboard.

## Variability is the third factor

Kingman's formula extends this to realistic arrivals:

> **W ≈ ( ρ / (1-ρ) ) x ( (c²ₐ + c²ₛ) / 2 ) x S**

where c²ₐ and c²ₛ are squared coefficients of variation for arrivals and service times.

Queueing delay is proportional to variability. Halving service-time variance halves queueing delay at the same utilization, with no new hardware.

This is why these work:

- Separating slow and fast requests into different pools, removing head-of-line blocking
- Caching, which narrows the service-time spread as much as it lowers the mean
- Capping request size and rejecting unbounded queries
- Rate limiting bursty producers on the way in

It also explains why bursty traffic hurts more than its average suggests: high c²ₐ keeps the multiplier high even at moderate ρ.

## One shared pool beats many small pools

With c servers sharing one queue (M/M/c), the knee moves right. A shared pool of 20 tolerates far higher utilization than 20 pools of 1, because separate queues allow one server to idle while another has a backlog.

- Prefer one shared work queue with N workers over N per-worker queues.
- Consistent-hash routing that pins keys to nodes reintroduces stranding. It buys cache locality and costs queueing efficiency, so choose deliberately. See `consistent-hashing`.
- Power of two choices (sample two servers, pick the shorter queue) recovers most of the shared-queue benefit without central coordination.

## Queues do not add capacity

A queue converts a throughput problem into a latency problem. It absorbs a burst and does nothing for sustained overload: when arrival rate exceeds service rate, the queue grows without bound and everything in it is late.

1. **Bound every queue.** An unbounded queue fails by becoming infinitely slow instead of visibly rejecting work. Rejecting is better, because the caller learns immediately while it can still act.
2. **Size the bound with Little's Law.** Depth L at drain rate λ implies latency L/λ. Past the client timeout, all that work is wasted.
3. **Shed rather than queue past that point.** Reject at the front door before allocating a thread or connection. See `retry-amplification`.
4. **Alert on queue depth.** It rises before latency does, making it the earliest usable signal.

## Utilization targets

| Workload | Steady-state target |
|---|---|
| Latency-sensitive request/response | 50-70% |
| Async, batch, queue workers | 80-90%, latency is not the goal |
| Bursty arrivals | Lower, since the burst is what is being sized for |
| Single-threaded hot path (event loop, single shard) | Below 60%, no parallelism to absorb variance |

The headroom is not waste. It is what buys the latency.

## The same math for teams

Little's Law does not care that the servers are people. WIP = arrival rate x cycle time.

- Cutting WIP shortens cycle time proportionally, which is the mechanism behind kanban WIP limits.
- A team at 100% utilization has unbounded queueing delay for new work, by the same curve.
- Cycle time is far more sensitive to WIP than to individual effort.
