---
name: hyrums-law
description: This skill should be used when the user asks "is this a breaking change", "can I change this undocumented behavior", "why did an internal change break a consumer", "how do I stop people depending on this", or is changing observable behavior never promised in a contract, such as iteration order, error message text, timing, sort stability, ID format, or JSON key order.
---

# Hyrum's Law

> With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody.

Hyrum Wright, at Google. This is the practical definition of a breaking change. A documented contract describes what was intended. Users' code describes what was actually promised.

## What gets depended on

| Behavior | How it becomes a dependency |
|---|---|
| Hash map iteration order | A test asserts on serialized output and passes for two years |
| Error message text | Consumer does `if (err.message.includes("not found"))` |
| Sort stability | UI relies on equal elements keeping insertion order |
| Timing | A call that took 5ms takes 50ms and a caller's timeout fires |
| Timing, inverted | A call gets faster and exposes a race the slowness was hiding |
| JSON key order | Consumer hashes the serialized body for a signature or cache key |
| Log line format | Someone's alerting greps it |
| ID format | Consumer parses a UUID for a timestamp, or assumes numeric ids |
| Float formatting | `0.1` versus `0.10` breaks a string comparison |
| Undefined-behavior results | An out-of-range index returned empty instead of throwing |
| Null versus missing field | Consumer distinguishes `{"x": null}` from `{}` |
| Header casing, redirect count, TLS cipher | Client hardcodes what it observed |

Rule of thumb: if a user can observe it, assume someone has written an `if` on it.

## Primary defense: make unspecified behavior unstable

Deliberately vary behavior that was never promised, so no dependency can form. This surfaces the dependency as a fast, loud test failure instead of a slow production break years later.

Precedents:

- **Go randomizes map iteration order** on every run, specifically so no program can depend on it.
- **Abseil randomizes its hash seed per process**, so container ordering differs between runs.
- Some services **inject a randomly named junk field** into JSON responses, forcing consumers to tolerate unknown fields.
- **Small random jitter in response latency** stops consumers tuning timeouts to an observed p50.
- **Randomized test execution order** (`go test -shuffle=on`) prevents inter-test dependencies.

Apply this to new APIs. Vary ordering, spacing, non-semantic identifiers, and optional-field presence.

## For existing systems: measure first

The dependency already exists. Determine whether it does rather than reasoning about whether it should.

1. **Instrument the specific behavior**, not the endpoint. Count reads of the field, calls hitting the deprecated path, clients sending the old header, tagged by caller identity.
2. **Watch for a full business cycle.** Monthly billing, quarterly reports, and annual renewals surface after a release.
3. **Canary the change.** Consumer breakage appears as their errors, so watch their error rate rather than only local metrics.
4. **Do not rely on a changelog note.** Use metrics, then deprecation with a deadline, then removal. See `expand-contract`.

## Designing to retain freedom

- **Return opaque types.** A pagination cursor should be an opaque signed string, not base64-encoded offsets. Anything readable will be decoded and constructed by hand.
- **Do not leak internals into observable output.** Stack traces, internal ids, and enum numbering all become contracts.
- **Supply what people are hacking around.** If everyone parses the logs, ship a structured API. If everyone regexes an error message, ship a stable machine-readable `code` field.
- **Separate the two layers explicitly**: a stable `code` that is promised, and a `message` explicitly reserved for rewording. Then reword it occasionally so the reservation stays credible.
- **Prefer loud failure to quiet drift.** Removing a field breaks visibly. Silently changing its meaning produces wrong data.

## Interaction with semver

Semantic versioning covers the documented contract. Hyrum's Law covers everything else, so a patch release can break real users.

This is not an argument against semver, but against treating a version number as a guarantee about impact rather than a claim about intent. Consequences:

- Test against major consumers, not only the local test suite.
- A behavior with enough dependents is part of the contract regardless of intent. Sometimes the correct action is to document what was accidentally promised and keep it.
- Bug-for-bug compatibility is a legitimate requirement. "It was a bug" is not by itself sufficient reason to change a mature interface.

## The inverse: Chesterton's Fence

The same law running backwards. A strange conditional, a redundant check, or an uncommented sleep usually exists because something observable depended on it. Find out what before removing it:

```bash
git log -S 'the exact odd line' --oneline -- path/to/file
```

The commit and its PR discussion usually answer the question in two minutes.

## Two review questions

1. **Can a user observe this difference?** If yes, it is potentially breaking regardless of the documentation.
2. **How would anyone know if someone depended on it?** If the answer is "we would not", add the metric before shipping the change.
