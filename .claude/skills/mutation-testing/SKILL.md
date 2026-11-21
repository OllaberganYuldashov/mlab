---
name: mutation-testing
description: This skill should be used when the user asks "are our tests actually good", "is 100% coverage meaningful", "what is mutation testing", "how do I measure test quality", "which tests are worthless", or is setting a coverage target or reviewing a test suite that passes while bugs still ship. Covers whether existing assertions detect bugs. For testing code with no known correct output use `metamorphic-testing`.
---

# Mutation testing

## The problem with coverage

Line coverage measures which lines **ran**, not which lines were **checked**. A test suite calling every function and asserting nothing scores 100%.

```python
def test_calculate():
    calculate(10, 5)      # 100% coverage of calculate(), zero assertions
```

Branch coverage is better and has the same flaw. Coverage is a necessary condition, not a sufficient one: low coverage proves tests are missing, high coverage proves nothing.

Mutation testing answers the actual question: **if the code were wrong, would a test fail?**

## How it works

1. Make a small change to the source, a **mutant**: `>` becomes `>=`, `+` becomes `-`, a boolean is negated, a return value becomes null, a statement is deleted.
2. Run the test suite.
3. If a test fails, the mutant is **killed**, meaning the tests detect that error.
4. If all tests pass, the mutant **survived**, meaning that line can be wrong and nothing notices.

> Mutation score = killed mutants / total mutants

A surviving mutant is a precise, actionable statement: *this exact change breaks nothing.* Either a test is missing, or the code is dead.

## Reading the output

Each surviving mutant is one of three findings:

| Finding | Meaning | Action |
|---|---|---|
| **Missing assertion** | The code runs but nothing checks the result | Add the assertion. This is the common case and the valuable one |
| **Dead or unreachable code** | The mutant cannot change behavior because nothing depends on it | Delete the code |
| **Equivalent mutant** | The mutation produces genuinely identical behavior, for example `i < n` versus `i != n` in a loop guaranteed to reach `n` | Nothing to fix. This is the tool's irreducible false-positive rate |

Equivalent mutants are undecidable in general, so no tool eliminates them. They typically account for a few percent of survivors. Suppress them explicitly rather than pretending the score can reach 100%.

## Tools

| Language | Tool |
|---|---|
| Java | PIT (`pitest`), the most mature |
| Python | `mutmut`, `cosmic-ray` |
| JS/TS | Stryker |
| C# | Stryker.NET |
| Go | `go-mutesting`, `ooze` |
| Rust | `cargo-mutants` |
| PHP | Infection |

## Making it practical

Mutation testing is expensive: the test suite runs once per mutant, so a suite taking 2 minutes with 500 mutants is 16 hours naively.

Controls that make it usable:

- **Run on the diff only.** Mutate changed lines in a PR, not the whole codebase. This is the single change that makes it viable, and most tools support it (`pitest` incremental analysis, Stryker `--since`).
- **Scope to critical modules.** Payment calculation, permission checks, and pricing deserve it. A CRUD controller does not.
- **Run nightly, not per commit**, for the full suite.
- **Use test selection**, where the tool runs only tests covering the mutated line. Every mature tool does this by default.
- **Fail the build on new survivors**, not on an absolute score. A ratchet works where a target does not.

## Interpreting the score

Do not target 100%. Equivalent mutants make it unreachable, and chasing it produces tests asserting implementation details.

| Score | Reading |
|---|---|
| Below 50% | Tests largely execute code without checking it |
| 60-80% | Typical for a healthy suite |
| Above 90% | Strong, usually only worth reaching in critical modules |

The score matters less than the survivor list. Read the survivors in the code that matters and fix those.

## Why the survivors are the point

A surviving mutant in a pricing function is a statement that pricing can silently change and the suite stays green. That is a concrete, prioritized bug report about the test suite, which coverage percentages never provide.

It also finds a specific failure mode nothing else catches: **tests that assert the wrong thing**. A test asserting `result is not None` passes for every mutant that changes the value, and mutation testing surfaces exactly that.

## Relationship to other measures

- **Coverage** finds untested code. Mutation testing finds unchecked code. Run coverage first, since mutation testing on uncovered lines only reports that they are uncovered.
- **Property-based testing** generates inputs. Mutation testing evaluates assertions. They are complementary: property tests often kill mutants that example-based tests miss, because they assert invariants rather than specific values.
- **`metamorphic-testing`** helps where the correct output is unknown, which is the case mutation testing cannot help with, since it presumes assertions are possible.

## Where not to use it

- Suites with flaky tests. A flaky test kills mutants at random and the score is noise. Fix flakiness first.
- Suites slower than a few minutes without diff scoping, where the feedback loop is too slow to act on.
- Generated code, glue code, and thin adapters, where survivors are mostly equivalent mutants.
