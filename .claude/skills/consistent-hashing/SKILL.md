---
name: consistent-hashing
description: This skill should be used when the user asks "how do I shard this data", "how do I add a node without rehashing everything", "what is consistent hashing", "should I use rendezvous hashing", "how do I fix a hot shard", or is designing key partitioning or cache sharding across a changing set of nodes. Covers distributing keys across nodes. For caching behavior of a single hot key use `cache-stampede`.
---

# Consistent hashing and its alternatives

## The problem with modulo hashing

```python
node = hash(key) % N
```

Adding or removing one node changes `N`, so almost every key moves. Going from 10 nodes to 11 relocates about 91% of keys: a near-total miss storm for a cache, a full data migration for a database.

Requirement: when N changes by one, only about `1/N` of keys should move.

## Ring (consistent hashing)

Hash both nodes and keys onto a circular space. A key belongs to the first node clockwise from its position. Adding a node captures only the keys between it and its predecessor.

**Virtual nodes are mandatory.** With one point per node, randomly placed points produce very unequal arc lengths and badly uneven load. Place each physical node at 100 to 200 ring positions:

```python
ring = {}
for node in nodes:
    for i in range(150):
        ring[hash(f"{node}#{i}")] = node
# bisect for the first position clockwise
```

Virtual nodes also provide weighting: a machine with twice the capacity gets twice the positions.

Used by DynamoDB, Cassandra, Riak, memcached clients, and most CDNs.

## Rendezvous hashing (highest random weight)

Simpler and better in most respects. Hash the key against every node, pick the highest score:

```python
def pick(key, nodes):
    return max(nodes, key=lambda n: hash(f"{key}:{n}"))
```

| Property | Rendezvous | Ring |
|---|---|---|
| State to maintain | None | Sorted ring of virtual nodes |
| Distribution | Naturally even | Needs 150+ virtual nodes to be even |
| Top-k replicas | Take the k highest scores | Walk clockwise skipping duplicate physical nodes |
| Lookup cost | O(N) | O(log N) |
| Keys moved on change | Minimal | Minimal |

Prefer rendezvous hashing under a few hundred nodes, which covers most systems, and especially when selecting replicas. Prefer a ring when node count makes O(N) lookups too expensive. Weighted rendezvous hashing (`-weight / log(h)` scoring) handles heterogeneous capacity.

## Jump consistent hash

For numbered buckets `0..N-1` where buckets are only added or removed **at the end**:

```
int32_t jump(uint64_t key, int32_t num_buckets)
```

Google's algorithm: five lines, no memory, faster than either alternative, perfectly balanced. The restriction is real, since an arbitrary node in the middle cannot be removed. Correct for resizable shard ranges, wrong for dynamic membership.

## Hot shards

Consistent hashing distributes **keys** evenly and says nothing about **traffic**, which is rarely uniform.

| Fix | Trade |
|---|---|
| **Micro-partitioning**: many more partitions than nodes (about 20 per node) assigned by a lookup table | Hot partitions move individually without rehashing. Adds a partition map to maintain |
| **Selective replication** of hot keys only | Targets the actual imbalance. Reads must choose among replicas |
| **Key splitting**: `key#0` to `key#N`, readers pick at random | Fixes a single hot key. Multiplies writes |
| **Local L1 cache** in front of the shard | Simplest and often most effective. Bounded staleness. See `cache-stampede` |

A single key hotter than one node's capacity cannot be fixed by any hashing scheme, since the key is indivisible. Splitting or replicating it is the only option.

## Cost of pinning keys to nodes

Routing a key to a fixed node buys cache locality and costs queueing efficiency, since per-node queues let one node idle while another has a backlog. See `queueing-and-utilization`.

Where cache locality is not the goal, prefer a shared queue, or **power of two choices**: sample two nodes and send to the shorter queue, which recovers most of the shared-queue benefit without coordination.

## Requirements in practice

- **Use a well-distributed, stable hash.** MurmurHash3 or xxHash. Never Python's `hash()`, randomized per process, or Java's `String.hashCode`, poorly distributed. Different clients must compute identical placements.
- **Every client must agree** on hash function, node list, and virtual-node count. A mismatch silently splits the keyspace.
- **Plan membership propagation.** While clients disagree, keys land in two places: a miss for a cache, a correctness bug for a database, requiring coordinated handoff.
- **Select distinct physical nodes for replicas**, not the next k ring positions, which may belong to one machine.
- **Respect failure domains.** Filter candidates by rack or zone, or all three replicas may share one rack.

## Choosing

| Situation | Use |
|---|---|
| Under a few hundred nodes, replicas needed | **Rendezvous hashing**, the simplest correct answer |
| Many nodes, lookup cost matters | Ring with 150+ virtual nodes each |
| Resizable numbered shards, no arbitrary removal | Jump consistent hash |
| Uneven traffic or frequent rebalancing | Micro-partitioning with an explicit partition map |
| Range scans by key are required | None of these. Use range partitioning |

The last row matters: hash partitioning destroys key order, so range queries fan out to every shard. Where queries are ranges over the partition key, range partitioning is correct despite its rebalancing cost.
