---
name: cache-stampede
description: This skill should be used when the user asks "how do I stop a thundering herd", "why does load spike when a cache key expires", "how should I set cache TTLs", "how do I handle cache misses for keys that do not exist", or reports many identical origin requests after an expiry, a spike after a cache flush or deploy, or one key saturating a cache node. Covers cache-expiry herds specifically. For retry storms and load shedding use `retry-amplification`.
---

# Cache stampede and related failures

Four distinct cache failure modes with four distinct fixes. Conflating them leads to applying the wrong remedy.

## 1. Stampede: thundering herd on expiry

A hot key expires. Before it is repopulated, every concurrent request misses and recomputes the same value. A key served at 1,000 req/s with a 500ms recompute produces about 500 simultaneous identical origin queries at each expiry.

The recompute is then slower because 500 are running, which widens the window and admits more requests. Under enough load this does not recover, which is a metastable failure. See `retry-amplification`.

### Fix A: probabilistic early expiration (XFetch)

The most effective fix and the least known. Each reader independently refreshes slightly early, with probability rising as expiry approaches. No locks and no coordination.

Store the recompute cost alongside the value:

```python
value, delta, expiry = cache.get(key)      # delta = seconds the last recompute took
if value is None or now() - delta * BETA * math.log(random.random()) >= expiry:
    value = recompute()
    cache.set(key, (value, elapsed, now() + ttl), ttl)
return value
```

`-log(random())` is an exponential random variable, so refresh probability rises smoothly toward expiry and scales with recompute cost. `BETA = 1` is a good default, higher refreshes earlier.

Result: almost always exactly one client refreshes, before expiry, while the cached value is still served. No request waits. From Vattani, Chierichetti and Lowenstein, *Optimal Probabilistic Cache Stampede Prevention* (VLDB 2015).

### Fix B: single-flight

One caller recomputes while the rest wait on the same in-flight result.

```go
v, err, _ := group.Do(key, func() (interface{}, error) { return recompute() })
```

In-process single-flight collapses N goroutines to 1 per instance. Across 50 instances that is 50 origin calls rather than 1, which is usually acceptable. For fleet-wide coalescing use `SET key value NX PX 5000` in Redis with losers serving stale. Distributed locks add failure modes (holder dies, lock expires mid-work), so prefer Fix A or in-process single-flight unless the recompute is genuinely expensive.

### Fix C: stale-while-revalidate

Two TTLs, soft and hard. Past the soft TTL serve stale and refresh in the background. Only past the hard TTL block and recompute.

```
soft 60s / hard 600s
   t < 60s   -> serve fresh
  60s-600s   -> serve stale, trigger one background refresh
   t > 600s  -> block and recompute
```

Standard in HTTP as `Cache-Control: stale-while-revalidate`. Trades bounded staleness for removal of user-visible recompute latency, which is usually the right trade.

## 2. Penetration: misses that can never hit

Requests for keys that do not exist miss every time and reach the origin. Any user-supplied identifier is an attack surface, since a loop over random IDs bypasses the cache entirely.

- **Negative caching**: cache the not-found result with a short TTL of 30 to 60 seconds, short so newly created objects appear quickly.
- **Bloom filter** in front for a large mostly-static key space, answering "definitely absent" in a few bits per key.
- **Validate the key shape** before any lookup.

## 3. Avalanche: mass simultaneous expiry

Many keys expire at the same instant because they were populated at the same instant, after a deploy, flush, failover, or nightly warm.

The fix belongs on every `set`:

```python
cache.set(key, value, ttl=base_ttl + random.uniform(0, base_ttl * 0.1))
```

After a flush or cold start, ramp traffic rather than opening the gate. A cold cache under full traffic is the classic metastable failure.

## 4. Hot key: one key exceeds one node

A single key lives on a single shard. Enough traffic saturates that node while the cluster idles, and sharding cannot help because the hash cannot split one key.

- **L1 in-process cache** with a 1 to 5 second TTL. Highest-leverage fix, and it also removes network round trips.
- **Key splitting**: write to `key#0` through `key#N`, readers pick at random. Costs N times the writes.
- **Client-side hot-key detection** promoting top keys to local cache automatically.

## The underlying rule

A cache must be an optimization, not a dependency.

Ask directly: if the hit rate went to zero right now, would the system stay up? A "no" means the cache is a fast single point of failure, and every mode above becomes an outage rather than a slowdown.

Verify it. Run a cache-flush drill in staging under production-like load. Most teams discover their cache is actually their database.

## Design checklist

1. Jitter on every TTL
2. Stampede protection on expensive keys, via XFetch or single-flight
3. Negative caching for anything keyed by user input
4. Known and tested behavior at 0% hit rate
5. Monitor **origin QPS**, not only hit ratio. A stampede is invisible in a hit-ratio graph
6. Alert on hit-ratio drops, which lead the outage
7. Bounded cache size with a sane eviction policy
