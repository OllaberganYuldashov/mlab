---
name: universal-scalability-law
description: This skill should be used when the user asks "why does adding servers not help", "why did throughput drop when we scaled out", "how far can this scale", "why is a bigger thread pool slower", or wants to fit a scalability curve to load test data or predict a capacity ceiling. Covers throughput that peaks then declines. For sizing a pool to a target latency use `queueing-and-utilization`.
---

# Universal Scalability Law

## The model

Adding workers helps, then stops helping, then starts hurting. Neil Gunther's USL puts a number on where each of those turns happens. Relative throughput at N workers:

```
C(N) = N / (1 + α(N-1) + βN(N-1))
```

| Term | Name | Cause |
|---|---|---|
| **α** | Contention | Serialized work: locks, single-threaded sections, a shared queue |
| **β** | Coherency | Cross-talk: every worker must agree with every other one |

Setting β = 0 gives Amdahl's law: throughput approaches a ceiling of 1/α and stays there.

With β > 0 the curve does not plateau. It **peaks and then declines**. Adding capacity past the peak makes the system slower. That is the result worth knowing, and it is why "just add more servers" sometimes makes an incident worse.

The peak is at:

```
N_max = sqrt((1 - α) / β)
```

## Why coherency is quadratic

Contention scales with N: everyone waits for one lock. Coherency scales with N², because keeping N workers consistent takes N(N-1)/2 pairwise exchanges.

Real sources of β:

- Cache-line ping-pong between cores (a shared counter, a hot mutex)
- Distributed consensus and quorum writes
- Gossip and membership protocols
- Cache invalidation broadcast to every node
- Distributed locks
- Read-repair and anti-entropy traffic
- Any "tell everyone" step

Typical magnitudes: α of 0.02-0.10 is common. β of 0.0001 sounds negligible and puts the peak at about 100 nodes.

## Fitting it to measured data

Fitting needs throughput at three or more load levels. Measure carefully first, since a load test with coordinated omission yields a fitted curve of nonsense. See `coordinated-omission`.

```python
import numpy as np
from scipy.optimize import curve_fit

def usl(n, alpha, beta):
    return n / (1 + alpha*(n-1) + beta*n*(n-1))

n = np.array([1, 2, 4, 8, 16, 32])
x = np.array([1.0, 1.9, 3.6, 6.2, 9.1, 10.3])   # throughput relative to N=1

(alpha, beta), _ = curve_fit(usl, n, x, p0=[0.05, 0.001], bounds=(0, 1))
print(f"alpha={alpha:.4f} beta={beta:.6f} peak at N={np.sqrt((1-alpha)/beta):.0f}")
```

Reading the fit:

| Result | Meaning | Action |
|---|---|---|
| α high, β ~ 0 | Serialization dominates | Find the lock or the single-threaded stage. There is a ceiling but no cliff |
| β measurably > 0 | Coherency dominates | There is a peak. Find it, and cap deployment below it |
| Both near 0 | Genuinely scalable in the measured range | Extrapolate cautiously, since β often appears only past the tested range |

Fitting on 2 or 3 points overfits. Use at least 5, including points past the knee where possible, since that is where β becomes identifiable.

## Acting on it

**Reduce α (contention)**

- Shard state so workers touch disjoint data
- Replace locks with per-worker structures aggregated at the end
- Batch to amortize the serialized section
- Remove single coordinator stages from the hot path

**Reduce β (coherency)**

- Weaken consistency where the product allows: eventual instead of strong
- Partition so agreement is needed only within small groups, not globally
- Replace broadcast invalidation with TTLs. See `cache-stampede`
- Reduce replica count for writes, or use quorums that do not require all nodes
- Hierarchical aggregation instead of all-to-all

Reducing β is usually an architecture change rather than a tuning change. That is the point of measuring it: it distinguishes a design limit from a configuration one.

## Where this applies day to day

- **Thread pools that get slower with more threads.** This is β from cache-line contention. Measure it before raising the pool size again. See `queueing-and-utilization`.
- **Database connection counts.** More connections past the peak reduce throughput. Same curve, and the reason pool sizing formulas give small numbers. See `connection-pooling`.
- **Adding nodes during an incident.** Past N_max, scaling out is actively harmful. Knowing this in advance prevents a common mistake.
- **Capacity planning.** Linear extrapolation from a 4-node test to 40 nodes is wrong in a specific, predictable direction.

## Limits of the model

USL is a curve fit, not a mechanism. It gives the shape and roughly where the limit sits, not which lock is responsible. Use it to decide whether the problem is contention or coherency, then profile to find the specific cause.

It also assumes homogeneous workers and a fixed workload mix. A heterogeneous fleet or a changing request mix will not fit cleanly, and forcing a fit produces confident wrong numbers.
