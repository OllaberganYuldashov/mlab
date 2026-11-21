---
name: coordinated-omission
description: This skill should be used when the user asks "why is production latency worse than our load test", "is this benchmark trustworthy", "how do I aggregate p99 across servers", "which load testing tool should I use", or when writing or interpreting a load test whose p99 looks suspiciously good. Covers whether latency numbers are measured correctly. For reducing an accurately measured tail use `tail-latency`.
---

# Coordinated omission

Most load tests carry this bug, and it understates tail latency by orders of magnitude, always in the flattering direction. Named by Gil Tene, creator of HdrHistogram.

A load generator that sends the next request only after the previous response arrives stops sending requests exactly when the system is slowest. The stall is never measured, because no requests were in flight during it. The system is graded only on requests it served promptly.

> The load generator coordinates with the system under test to omit the bad results.

## The arithmetic

Send one request every 10ms for 100 seconds, so 10,000 requests. The server handles 9,999 in 1ms, then freezes for 100 seconds on the last one.

**Closed-loop harness reports**: 9,999 samples of 1ms plus one of 100s. p99 = 1ms.

**What actually happened**: during the freeze, 10,000 requests should have been sent. They would have waited 100s, 99.99s, down to 0. The real median is about 50 seconds.

Same run. One measurement says 1ms at p99, the honest one says 50s at p50.

## Where it hides

- Any thread-per-user harness with a request loop, which is the default shape of hand-rolled tests
- `wrk`, `ab`, and most homegrown scripts, closed-loop by construction
- JMeter and Gatling configured with think time between iterations, where the think time absorbs the stall
- **Server-side metrics that start the timer in the handler.** Time in the accept queue, thread pool queue, or connection pool is omitted, so the service reports 5ms while clients see 500ms
- Any bounded queue where only admitted requests are measured. Shed and rejected requests vanish from the distribution, and they were the worst ones

## Client-side fix: open-loop generation

Decide when each request should be sent, independently of when the system responds, and measure from that intended time.

```python
start = now()
for i in range(n):
    intended = start + i * interval      # fixed schedule, never slips
    wait_until(intended)                 # returns immediately when behind
    send_request()
    record(now() - intended)             # from intended, not from actual send
```

The last line is the one that matters. Recording `now() - actual_send_time` reintroduces the bug.

Alternatively correct after the fact with HdrHistogram, which synthesizes the omitted samples:

```java
histogram.recordValueWithExpectedInterval(latencyNanos, expectedIntervalNanos);
```

Correction assumes a uniform arrival pattern, so prefer generating load correctly.

## Tool selection

| Tool | Status |
|---|---|
| `wrk2` | Written specifically to fix this. Constant throughput, corrected latency |
| Gatling open injection (`constantUsersPerSec`) | Correct |
| k6 `constant-arrival-rate` executor | Correct. The default `constant-vus` executor is closed-loop |
| JMeter | Needs the Throughput Shaping Timer plus care. Not correct by default |
| `wrk`, `ab` | Closed-loop. Fine for throughput, wrong for tail latency |

Heuristic: a tool asking for a **rate** is probably open-loop. A tool asking for a number of **threads or VUs** is probably closed-loop.

## Second error: averaging percentiles

Percentiles cannot be averaged. The mean of ten servers' p99 values is not the fleet p99, and neither is the max or the p99 of per-minute p99s. No arithmetic recovers a combined percentile from separate percentiles.

Aggregate histograms instead:

- HdrHistogram is mergeable. Sum the buckets, then read the percentile.
- Prometheus `histogram_quantile()` over `rate(..._bucket[5m])` works because it operates on buckets. Prometheus **summaries cannot be aggregated across instances**, which is the documented reason to prefer histograms.
- Store bucket counts in the metrics pipeline, not precomputed p99 values.

The same rule applies across time: a daily p99 is not the average of 1,440 per-minute p99 values.

## Reporting latency honestly

- **Report p99, p99.9, p99.99, and max.** A session making 100 requests hits p99 roughly 63% of the time. See `tail-latency`.
- **State the load level.** Latency without a request rate is uninterpretable, since latency is a function of utilization. See `queueing-and-utilization`.
- **Include failed and shed requests.** Excluding them means a system that rejects everything scores perfectly.
- **Plot the full percentile distribution** on a log-scaled x axis. A knee at p99.9 means something different from a knee at p50.
- **Report run-to-run variance.** One number from one run is not a measurement.

## Load test checklist

1. Load generated at a fixed rate independent of responses
2. Latency measured from the intended send time
3. Server-side timer started at request arrival, including queue wait
4. Errors, timeouts, and shed requests present in the distribution
5. Percentiles computed from merged histograms, never averaged percentiles
6. Reported numbers tied to a stated load level and duration

Any "no" makes the tail numbers decorative.
