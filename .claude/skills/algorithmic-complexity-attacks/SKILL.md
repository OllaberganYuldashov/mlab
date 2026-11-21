---
name: algorithmic-complexity-attacks
description: This skill should be used when the user asks "is this regex safe", "what is ReDoS", "why does CPU spike on one request", "how do I safely accept uploads or XML", "is this parser safe against untrusted input", or is reviewing a regex over user input, handling compressed files, or responding to a ReDoS advisory.
---

# Algorithmic complexity attacks

Most code is fast on average and slow in the worst case. An algorithmic complexity attack is an attacker choosing the worst case deliberately. No memory corruption and no injection, just input costing 100,000 times more to process than to send.

The economics make it dangerous: a 50-byte request burning 30 seconds of CPU lets one laptop saturate a fleet, and it bypasses rate limiting because the request rate is trivially low.

## 1. ReDoS: catastrophic backtracking

Most engines (PCRE, Java, JavaScript, Python `re`, .NET, Ruby) backtrack. On a non-match they try every way to divide the input among quantifiers. When two quantifiers can match the same characters, the number of ways is exponential.

Vulnerable shapes:

```
(a+)+          nested quantifier
(a|a)*         alternation with overlapping branches
(a|ab)*        overlapping alternatives
\s*$           trailing quantifier with an anchor on a long whitespace run
^(\w+\s?)*$    the classic, since \w and \s? both consume the boundary
```

The general rule: **two quantified subexpressions that can match the same character**.

```python
re.match(r'^(\w+\s?)*$', 'a' * 30 + '!')   # seconds
re.match(r'^(\w+\s?)*$', 'a' * 40 + '!')   # hours
```

The trailing `!` matters. Blowup happens on the **failed** match, after every alternative is exhausted, so rejected input is what costs. That makes validation regexes the prime target.

Notable outages: Stack Overflow 2016 (a `\s+$` trim regex), Cloudflare 2019 global outage (`.*.*=.*` in a WAF rule), plus a long series of npm CVEs.

### Fixes in order

1. **Do not use a regex.** Most vulnerable patterns validate email, URLs, or dates. Use a parser or a library. This eliminates the class.
2. **Use a linear-time engine.** RE2 (Go's `regexp`, plus bindings for Python, Node, Ruby) and Rust's `regex` crate guarantee linear time. They drop backreferences and lookaround, which are the features enabling blowup.
3. **Bound input length before matching.** Exponential blowup needs length, so a 256-character cap caps the damage.
4. **Rewrite the pattern** so alternatives are disjoint: `(\w+\s?)*` becomes `\w+(\s\w+)*`, `(a|ab)*` becomes `(ab?)*`.
5. **Use atomic groups or possessive quantifiers** (`(?>...)`, `a++`) where supported, which forbid backtracking into the group. Java and PCRE support this, JavaScript does not.
6. **Set a timeout** as a backstop. .NET supports regex timeouts, Java does not, so elsewhere run untrusted matching in a worker with a deadline.

**Never accept a user-supplied regex.** That is remote code execution against CPU. Where a search pattern must be offered, run it on RE2 with a length cap and timeout in an isolated worker.

Detection tools: `redos-detector`, `recheck`, `safe-regex`, Semgrep and CodeQL rules. Also grep for the shapes directly: nested quantifiers, `(...)*` containing `|`, and `\s*$`.

## 2. Hash flooding

Hash tables are O(1) average and O(n) worst case. Keys chosen to collide make every insert a linear scan, so inserting n keys costs O(n²). Send a JSON object with thousands of colliding keys. This took down PHP, Python, Ruby, Java, and Node simultaneously in the 2011 disclosure.

The fix is randomized hash seeds, now default in most runtimes:

- Python since 3.3, via `PYTHONHASHSEED`. **Do not pin it in production**, which people do to make tests reproducible.
- Rust `HashMap` uses SipHash with a random seed. Swapping in `FxHashMap` for speed removes the protection, which is fine for internal keys and not for user input.
- Go maps randomize the seed.
- Java `HashMap` since 8 converts long collision chains to trees, giving O(log n) instead.

Still needing attention: hand-written hash maps, fast non-cryptographic hashes (FNV, xxHash) over attacker-controlled keys, and caches keyed by user input. Also cap the number of keys accepted in a parsed object.

## 3. Decompression and parser amplification

| Attack | Mechanism | Fix |
|---|---|---|
| **Zip bomb** | 42 KB expands to petabytes via nested or overlapping entries | Cap decompressed size and entry count, stream and abort past the limit. Never trust the declared size |
| **Zip slip** | Entry named `../../etc/cron.d/x` escapes the extraction directory | Resolve each path after normalization and verify it stays under the target root |
| **Billion laughs** | XML entities expanding recursively, 10 entities x 10 levels = 10¹⁰ | Disable entity expansion (`defusedxml`, `FEATURE_SECURE_PROCESSING`) |
| **XXE** | External entities read local files or make requests | Disable external entities and DTDs |
| **YAML bombs** | Anchors and aliases expand exponentially, some loaders instantiate classes | `yaml.safe_load` always, plus a document size cap |
| **JSON deep nesting** | 100,000 nested arrays overflow a recursive parser's stack | Cap nesting depth and body size at the edge |
| **Gzip bomb over HTTP** | A `Content-Encoding: gzip` request body expanding enormously | Cap decompressed request size before decompressing |

The general rule: **limit the output, not the input.** A size check on the compressed payload proves nothing.

## 4. Other worst cases

- **Quadratic string building.** `s += x` in a loop is O(n²) with immutable strings, and attacker-controlled length makes it a DoS.
- **Sorting with a user-supplied comparator.** An inconsistent comparator can loop or throw, and predictable-pivot quicksort has an O(n²) adversarial input.
- **Unbounded pagination or fan-out.** `?limit=1000000` is an attack requiring no cleverness. Cap server-side.
- **GraphQL query depth.** Deep nesting multiplies into millions of resolver calls. Enforce depth and complexity limits.
- **Timing side channels**, the inverse problem: use constant-time comparison (`hmac.compare_digest`, `crypto.timingSafeEqual`) for secrets, tokens, and signatures.

## Review checklist

1. Every regex over user input: linear-time engine, or input length capped?
2. Every parser at a trust boundary: size cap, depth cap, entity expansion disabled?
3. Every decompression: bounded output size and entry count?
4. Any hash map keyed by user input using a non-randomized hash?
5. Any pagination, fan-out, or query-depth parameter without a server-side maximum?
6. `PYTHONHASHSEED` or equivalent unpinned in production?

A request costing 30 seconds of CPU and then timing out will be retried, turning one payload into three. See `retry-amplification`.
