---
name: clocks-and-time
description: This skill should be used when the user asks "how do I measure elapsed time correctly", "why do timestamps disagree across servers", "how do I order events across machines", "should I use timestamptz", "why did the cron job run twice", or is handling time zones, DST, clock skew, or logical clocks. Covers wall-clock, monotonic, and logical clocks. For database transaction ordering use `isolation-anomalies`.
---

# Clocks and time

## Rule 1: never measure duration with the wall clock

Two different clocks exist, and mixing them is the most common time bug.

| Clock | Property | Use for |
|---|---|---|
| **Wall clock** (`time()`, `Date.now()`, `System.currentTimeMillis`) | Can jump forward or backward: NTP correction, DST, manual set, VM migration | Timestamps meant for humans or storage |
| **Monotonic** (`time.monotonic()`, `performance.now()`, `System.nanoTime`, `CLOCK_MONOTONIC`) | Never goes backward. Meaningless as an absolute value. Usually excludes suspend time | Durations, timeouts, rate limits, retries, benchmarks |

```python
start = time.monotonic()
do_work()
elapsed = time.monotonic() - start     # correct

start = time.time()                    # WRONG: an NTP step makes elapsed negative
```

Negative elapsed times, timeouts that never fire, and rate limiters that unlock for a minute all come from this. A backward NTP step of a few hundred milliseconds is routine.

Go's `time.Time` carries both readings and `Sub` uses the monotonic one automatically, but serialization strips it, so a round-tripped value loses the guarantee.

## Rule 2: NTP does not produce synchronized clocks

NTP typically keeps machines within a few milliseconds, but:

- Skew of **100ms or more is normal** under load or on VMs.
- Correction can be a **step** (instant jump) or a **slew** (rate adjustment). Steps break wall-clock durations.
- A machine with a broken or unconfigured NTP client can be off by minutes or years. This happens in every fleet.
- Google/AWS **smear leap seconds** over hours, so their clocks are deliberately wrong by up to 0.5s during the smear. Mixing smeared and unsmeared sources produces disagreement.

Consequence: **never compare timestamps from two machines to determine ordering.** Two events one millisecond apart on different hosts can carry timestamps in either order. Anything built on "later timestamp wins" is silently lossy.

## Rule 3: store timestamps unambiguously

| Do | Do not |
|---|---|
| `TIMESTAMPTZ` in Postgres (stores UTC, converts on read) | `TIMESTAMP` without time zone, which stores the value given with no record of its offset |
| UTC everywhere internally | Local time in storage or logs |
| ISO 8601 with offset: `2026-08-27T14:30:00Z` | `2026-08-27 14:30:00` with no offset |
| Store the **IANA zone name** (`Europe/Berlin`) for future events | Store a fixed UTC offset for a future event |

That last row matters and is often missed. A meeting at 09:00 Berlin time next March has no fixed UTC value today, because DST rules can change. For **past** events store the UTC instant. For **future** local-time commitments store the wall time plus the zone name, and resolve at use.

Other rules:

- Convert to local time only at the display layer.
- Do not use `%Z`/`%z` abbreviations like `CST` for parsing: they are ambiguous across countries.
- Set the DB session and container time zone to UTC explicitly so behavior does not depend on the host.
- Unix timestamps are unambiguous but discard the zone the user cared about. Store both when the local zone is meaningful.

## Rule 4: DST arithmetic is not addition

Adding 24 hours is not the same as adding one day. On a DST transition day, one day is 23 or 25 hours. Some local times do not exist (spring forward) and some occur twice (fall back).

```python
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

tz = ZoneInfo("America/New_York")
d = datetime(2026, 3, 7, 12, 0, tzinfo=tz)
d + timedelta(days=1)     # correct calendar day, handles the transition
```

Use a library that does calendar arithmetic in the zone (`zoneinfo`, `Temporal` in JS, `java.time`). Never do arithmetic on epoch seconds and convert afterward when the answer must be a local wall time.

Also: keep the `tzdata` package updated. Zone rules change several times a year by government decision.

## Ordering events across machines

Since wall clocks disagree, use logical clocks when order matters.

| Mechanism | Guarantee | Cost |
|---|---|---|
| **Lamport timestamp** | If A caused B, then `ts(A) < ts(B)`. The converse does not hold | One counter |
| **Vector clock** | Detects whether two events are concurrent or causally ordered | O(N) space per event, N = number of nodes |
| **Hybrid Logical Clock (HLC)** | Causality like Lamport, plus a value close to physical time | 64 bits, and it is readable as a timestamp |

**Lamport**: increment the counter on every local event, attach it on send, and on receive set `counter = max(local, received) + 1`.

**HLC** is the practical choice for most systems. It keeps a physical component and a logical counter, so timestamps stay within clock skew of real time while never going backward and always respecting causality. Used by CockroachDB, YugabyteDB, and MongoDB. The result is sortable, human-readable timestamps that are also correct for ordering.

**TrueTime** (Spanner) takes the other approach: expose clock uncertainty as an interval and wait it out before committing. This buys external consistency and costs a few milliseconds per commit, and it needs GPS and atomic clocks in every datacenter.

Where logical clocks are not adoptable, the fallback is to make ordering irrelevant: use idempotent operations and CRDTs, or route all writes for one key through a single node so only its local clock is involved.

## Scheduled jobs

- Cron in local time fires **twice** or **zero times** on DST transitions. Run schedulers in UTC.
- Jitter schedules across hosts, or every machine fires at `:00` simultaneously. See `retry-amplification`.
- Do not assume a job runs exactly once at exactly the scheduled time. Make handlers idempotent and derive the work window from data, not from "now".
- A job that processes "the last hour" using wall-clock `now()` will skip or double-process on a clock step. Track a persisted watermark instead.

## Checklist

1. Durations and timeouts on a monotonic clock
2. No cross-machine timestamp comparison used for ordering
3. `TIMESTAMPTZ` and UTC in storage, zone conversion at display
4. IANA zone names stored for future local-time events
5. Calendar arithmetic via a zone-aware library, not epoch math
6. `tzdata` kept current
7. Schedulers in UTC, handlers idempotent, watermarks persisted
