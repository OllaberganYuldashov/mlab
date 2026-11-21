---
name: write-amplification
description: This skill should be used when the user asks "should I use an LSM or a B-tree", "why is disk usage far bigger than my data", "why do writes slow down as data grows", "how do I tune RocksDB compaction", "what is write amplification", or is choosing a storage engine or database for a given read/write mix.
---

# Write amplification and the RUM conjecture

## The RUM conjecture

Every storage engine optimizes at most two of three overheads:

| Overhead | Definition |
|---|---|
| **R**ead amplification | Bytes read per logical read |
| **U**pdate amplification | Bytes written per logical write |
| **M**emory/space amplification | Bytes stored per logical byte |

No engine minimizes all three. Every engine is a position on this triangle, and every tuning knob moves along an edge. A claim that one engine is strictly better means a workload was chosen where the sacrificed dimension does not matter.

## The two families

| | B-tree (Postgres, InnoDB, SQLite) | LSM-tree (RocksDB, Cassandra, ScyllaDB) |
|---|---|---|
| Write path | Update page in place, write WAL | Append to memtable, flush, compact later |
| Write amp | 10-30x (page rewrite + WAL, random I/O) | 5-20x (sequential, but rewritten per level) |
| Read amp | Low: ~tree height | High: check memtable + N SSTables |
| Space amp | ~1.3x (page fragmentation) | 1.1x to 2x+ (obsolete versions until compacted) |
| Range scans | Good, data is ordered on disk | Worse, merge across levels |
| Latency profile | Predictable | Spiky, compaction stalls |

Rule of thumb: **B-tree for read-heavy and range-scan workloads. LSM for write-heavy workloads and slow random I/O.**

## Where B-tree write amplification comes from

Writing 100 bytes can cost 16 KB of I/O:

1. The page containing the row is 8 KB, and the whole page is rewritten.
2. The WAL entry is written first (write-ahead durability).
3. Postgres additionally writes the **entire page** to WAL on the first modification after a checkpoint (`full_page_writes`, protection against torn pages).
4. Every index whose columns changed is updated, each costing its own page write.

Reductions:

- Fewer indexes, especially on frequently updated columns.
- HOT updates in Postgres: leave page headroom with `fillfactor`, and do not index volatile columns. See `mvcc-and-bloat`.
- Longer checkpoint intervals amortize full-page writes over more changes, at the cost of longer recovery.
- Batch writes into fewer, larger transactions.

## Where LSM write amplification comes from

Data is written once to the memtable, then rewritten at every compaction level.

**Leveled compaction**: each level is ~10x the previous. Write amp is roughly `10 x number_of_levels`, commonly 10-30x. Space amp is low (~1.1x) and read amp is moderate.

**Tiered (size-tiered) compaction**: merge same-size files. Write amp is much lower, space amp is much higher (up to 2x, since obsolete versions linger), read amp is higher.

The knob is the same tradeoff restated: leveled buys space and reads with writes, tiered buys writes with space and reads.

## Tuning LSM engines

| Symptom | Cause | Fix |
|---|---|---|
| Write stalls, periodic latency spikes | Compaction cannot keep up | More compaction threads, rate-limit foreground writes, switch to tiered |
| Disk usage 2x logical data | Tiered compaction, obsolete versions | Switch to leveled, or trigger compaction |
| Slow point reads | Too many SSTables to check | Enable bloom filters (usually on), raise bits per key, more aggressive compaction |
| Slow range scans | Merge across levels | Leveled compaction, larger block cache |

Bloom filters are what make LSM point reads viable: they answer "definitely not in this SSTable" in a few bits per key, so a read checks only the files that might contain the key. They do not help range scans.

## Diagnosis

Compute the actual amplification rather than assuming it:

```
write_amp = bytes_written_to_disk / bytes_written_by_application
space_amp = bytes_on_disk / logical_data_size
```

| Source | Where |
|---|---|
| RocksDB | `rocksdb.stats` LOG file: per-level write amp and compaction stats |
| Postgres | `pg_stat_bgwriter` (buffers written), WAL volume via `pg_stat_wal` |
| InnoDB | `SHOW ENGINE INNODB STATUS`, pages written vs rows changed |
| OS | `iostat -x` write throughput versus the known logical write rate |

Write amp of 30x consumes rated SSD endurance 30x faster than the logical write rate suggests. This is how NVMe drives in write-heavy fleets fail years early.

## Choosing

| Workload | Engine |
|---|---|
| Read-heavy, complex queries, joins, range scans | B-tree (Postgres, InnoDB) |
| Write-heavy time series, logs, events | LSM (RocksDB, Cassandra), or a columnar store |
| Analytical scans over few columns | Columnar (ClickHouse, Parquet), which is a different point on the triangle: minimal read amp for scans, poor point lookups |
| Mostly appends, queried by time range | LSM or columnar, partitioned by time |
| Small dataset that fits in RAM | Amplification is mostly irrelevant. Pick for query features |

## Related knobs that are the same tradeoff

- **Compression** trades CPU for space and read amp. Usually worth it: less I/O often beats the CPU cost.
- **Page size / block size**: larger blocks help scans, hurt point reads and raise write amp.
- **Covering indexes** trade space and write amp for read amp. See `index-design`.
- **Materialized views** trade write amp and space for read amp.
- **Denormalization** is the same trade at the schema level.

Naming the axis makes these decisions fast: state which of R, U, or M is being spent, then confirm it is the one the workload can afford.
