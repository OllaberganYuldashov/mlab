---
name: metamorphic-testing
description: This skill should be used when the user asks "how do I test this when I do not know the expected output", "how do I test a search ranking or ML model", "what is the oracle problem", "how do I test a scientific computation or optimizer", or is testing code whose correct answer cannot be computed independently. Covers testing without a known correct answer. For judging whether existing tests are strong use `mutation-testing`.
---

# Metamorphic testing

## The oracle problem

Ordinary testing needs a known correct answer:

```python
assert add(2, 2) == 4
```

Much real code has no such oracle. What is the correct output of a search ranking, a route planner, a compiler optimization, a recommendation model, a physics simulation, a float-heavy numerical routine? Computing the expected answer independently would mean writing the program a second time.

The usual responses both fail. Asserting the current output freezes today's bugs as the specification (a golden test that certifies whatever it does now). Asserting only that it does not crash tests almost nothing.

## The technique

Do not assert what one output **is**. Assert how outputs **relate** when the input changes in a known way. That relation is a **metamorphic relation**.

```python
# no oracle, but a relation holds
results_a = search("machine learning")
results_b = search("machine  learning")     # extra whitespace
assert results_a == results_b               # normalization relation
```

The relation is checkable without knowing the right answer. When it breaks, there is a real bug.

This found hundreds of real bugs in GCC and LLVM (EMI testing), in SQL engines, and in commercial machine translation.

## Relation families

Ask what transformations of input should have a predictable effect on output.

| Family | Relation | Example |
|---|---|---|
| **Invariance** | Output unchanged | Reordering an unordered input, renaming variables, adding whitespace, permuting independent records |
| **Equivalence** | Different route, same result | `sum(xs)` equals `sum(reversed(xs))` within tolerance, two query plans, two code paths for the same operation |
| **Monotonicity** | Output moves in a known direction | Adding a matching document does not lower its corpus's result count. Raising a price does not raise predicted demand |
| **Inverse** | Round trip returns the original | `decode(encode(x)) == x`, `decompress(compress(x)) == x`, `parse(format(x)) == x` |
| **Subsumption** | A narrower query returns a subset | `search("red shoes")` results are a subset of `search("shoes")` results |
| **Scaling** | A proportional input change scales the output | Doubling every weight leaves the argmax unchanged |
| **Additivity** | Parts compose to the whole | `mean(a + b)` lies between `mean(a)` and `mean(b)` |

## Worked examples

**Compiler**: transform a program by inserting statements into provably dead code. The compiled output must behave identically. This is EMI (Equivalence Modulo Inputs) testing and it found hundreds of GCC and LLVM bugs.

**Database**: rewrite a query into a form guaranteed to be equivalent (add a redundant `WHERE TRUE`, reorder joins, push a predicate). The result set must be identical. This is how SQLancer finds engine bugs.

**Machine translation**: replace one noun with another noun of the same type. The sentence structure of the translation should stay the same. Divergence indicates a bug.

**Numerical code**: `solve(A, b)` should satisfy `A @ x ≈ b`. Checking the residual needs no oracle and no reference implementation. Also scale the system by a constant and confirm the solution scales.

**Search or recommendation**: adding an irrelevant document must not change the ranking of existing results.

## Combining with property-based testing

Metamorphic relations are properties, so a property-based framework generates the inputs and shrinks failures automatically:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_sort_is_permutation_invariant(xs):
    assert sorted(xs) == sorted(list(reversed(xs)))

@given(st.text())
def test_encode_decode_round_trip(s):
    assert decode(encode(s)) == s
```

Tools: Hypothesis (Python), fast-check (JS), QuickCheck and its ports, `proptest` (Rust), jqwik (Java).

Shrinking is the main practical benefit: a failure arrives as the smallest input that still breaks the relation, which is usually enough to diagnose it directly.

## Finding relations

Ask these in order:

1. What input changes should change **nothing**? These are the strongest and easiest relations.
2. What operation **undoes** this one? Round trips catch a great deal.
3. What input change should move the output in a **known direction**, even without a known magnitude?
4. What two different ways exist to compute the same thing? A slow obviously-correct implementation is an excellent oracle for a fast one.
5. What does the domain **guarantee** regardless of input? Conservation laws, totals matching, non-negativity, sums to one.

Item 4 deserves emphasis. Where a naive O(n²) reference implementation is easy to write, testing the optimized version against it is the strongest available test, and the reference need never ship.

## Limits

- **Relations can hold on broken code.** A function returning a constant satisfies many invariance relations. Combine relations, and combine them with example-based tests where an oracle does exist.
- **Tolerances need care in floating-point relations.** `sum(xs) == sum(reversed(xs))` is false for floats. Use a tolerance derived from the computation. See `floating-point`.
- **A failing relation identifies a bug, not its location.** It says the relation broke, not which of two runs is wrong.
- **Some relations are approximate by design**, for example a translation whose structure "should usually" be preserved. Approximate relations produce false positives and need a threshold, so state it explicitly.

Use `mutation-testing` to check whether these relations actually catch injected errors. A metamorphic test that kills no mutants asserts a relation too weak to matter.
