---
name: connascence
description: This skill should be used when the user asks "why is this so tightly coupled", "how do I decouple these", "is this coupling acceptable across a module boundary", or when reviewing positional arguments, magic values, required call ordering, shared mutable state, or duplicated algorithms. Provides a taxonomy that names and ranks kinds of coupling precisely.
---

# Connascence

Two pieces of code are connascent when changing one forces a change to the other to keep the program correct. Named by Meilir Page-Jones, 1992.

"Coupling" is a binary word, which makes it useless in review since everything is coupled to something. Connascence supplies a taxonomy and a ranking, converting "this feels tightly coupled" into "this is connascence of position across a package boundary", which names the fix.

## Three axes

Judge every instance on all three:

- **Strength**: how hard it is to refactor. See the ladder below.
- **Degree**: how many places are involved.
- **Locality**: how far apart they sit. Same function, same class, same module, same repo, different service.

The rule that ties them together:

> The further apart two things are, the weaker their connascence must be.

Strong connascence inside one small function is ordinary code. The same connascence spanning two services is an incident waiting to happen.

## The ladder

Static forms, visible by reading the code:

| # | Form | Both sides must agree on | Fix |
|---|---|---|---|
| 1 | **Name** | a name | Unavoidable and fine |
| 2 | **Type** | a type | Fine, this is what type systems do |
| 3 | **Meaning** | what a value means (`0` = success, `-1` = missing) | Named constants, enums, sum types |
| 4 | **Position** | order (positional args, tuple returns, CSV columns) | Named parameters, objects |
| 5 | **Algorithm** | that both compute identically (checksums, hashing, cursors) | One shared implementation |

Dynamic forms, visible only at runtime and considerably worse:

| # | Form | Both sides must agree on | Fix |
|---|---|---|---|
| 6 | **Execution order** | that `a()` runs before `b()` | Make the order impossible to get wrong |
| 7 | **Timing** | that something happens within a window | Locks, barriers, explicit waits |
| 8 | **Values** | that several values change together | One object, or one transaction |
| 9 | **Identity** | that two references point at the same instance | Pass the reference explicitly |

Dynamic connascence is worse because the compiler cannot see it, grep cannot find it, and violations surface as production bugs rather than build failures.

## Three rules for applying it

Jim Weirich's formulation:

1. Minimize overall connascence by splitting the system into encapsulated units.
2. Minimize connascence that crosses encapsulation boundaries.
3. Maximize connascence within an encapsulation boundary.

Rule 3 is the one most often missed. Concentrating strong connascence inside one module is the goal, not a failure. That is what encapsulation is for.

## Refactoring down the ladder

Each fix converts a stronger form into a weaker one.

**Meaning to Name**

```python
def find(xs, target): ...              # returns index or -1: every caller must know
def find(xs, target) -> int | None: ...  # the type says it
```

**Position to Name**

```python
create_user("ada", "lovelace", True, False, True)
create_user(first="ada", last="lovelace", admin=True, suspended=False, verified=True)
```

**Algorithm to Name.** When a client and a server each implement the same signing scheme, one change breaks the other at runtime. Publish a single shared implementation, or move the operation behind an endpoint.

**Execution order to nothing**

```js
const c = new Client(); c.connect(); c.send(msg);   // order matters
const c = await Client.connect(); c.send(msg);      // order is now impossible to get wrong
```

**Timing to Name**

```js
await sleep(200);                    // flaky, and slow when it passes
await waitFor(() => q.isEmpty());    // explicit condition
```

## Applying it in review

Replace a vague objection with this template:

> This is connascence of **\<form\>**, degree **\<n\>**, across **\<boundary\>**. Weaken it to **\<form\>** by **\<fix\>**.

Flag these specifically:

- A magic number or string appearing in more than one file: meaning, high degree
- Four or more positional parameters, or a tuple return read by many callers: position
- Two services that must deploy together: strong connascence across the strongest boundary present, fix this first
- "Call `init()` first" in a docstring: execution order
- `sleep()` in a test: timing
- Two rows that must update together outside a transaction: values

## Limits

No linter computes a connascence score, and attempts to build one are not worth the effort. This is a review and design vocabulary. Its value is making coupling arguments concrete enough to settle quickly.

Use `cyclomatic-complexity` to judge whether a function is hard to test. Use connascence to judge why a change is hard to make.
