---
name: floating-point
description: This skill should be used when the user asks "why is 0.1 + 0.2 not 0.3", "how do I compare floats", "what type should I use for money", "why is my total off by a cent", "why do sums drift", or reports NaN appearing unexpectedly, a test failing on a tiny difference, or results differing between machines.
---

# Floating point

## What a float is

An IEEE 754 `double` is `sign x mantissa x 2^exponent` with a 53-bit mantissa. It represents numbers of that form exactly and nothing else.

`0.1`, `0.2`, and `0.3` are not of that form:

```python
>>> from decimal import Decimal
>>> Decimal(0.1)
Decimal('0.1000000000000000055511151231257827021181583404541015625')
>>> 0.1 + 0.2 == 0.3
False
```

Not a language quirk. Binary cannot represent one tenth, just as decimal cannot represent one third.

Two consequences:

- Every decimal fraction typed into source is already an approximation before any arithmetic.
- **Float addition is not associative.** `(a + b) + c` can differ from `a + (b + c)`, which is why parallel and vectorized sums differ from sequential ones, and why the same code gives different results on different machines.

## Money: never a float

`0.1 + 0.2 != 0.3` means a total that should be `$0.30` can be `$0.30000000000000004`, and rounding at the wrong moment loses or invents money.

| Approach | Use |
|---|---|
| **Integer minor units**, cents as `int64` | Best default. Fast, exact, no library. Watch currencies with 0 or 3 decimals (JPY, KWD) |
| **Decimal type**: Python `decimal.Decimal`, Java `BigDecimal`, C# `decimal` | When division, percentages, or more than 2 places are needed |
| **`NUMERIC` in the database** | Never `FLOAT`, `REAL`, or `DOUBLE PRECISION` for money |

```python
Decimal('0.1') + Decimal('0.2') == Decimal('0.3')     # True, note the strings
Decimal(0.1)                                           # wrong, already lossy
```

Construct decimals from strings, never from floats.

Choose the rounding mode deliberately. Most languages default to banker's rounding (half-to-even), which is statistically better but usually not what accounting rules require. `ROUND_HALF_UP` is typically expected, so confirm rather than inheriting a default.

## Comparison

`==` on floats is almost always wrong, and so is a bare epsilon:

```python
abs(a - b) < 1e-9            # wrong for large values
abs(a - b) / abs(b) < 1e-9   # wrong near zero
```

Use combined absolute and relative tolerance:

```python
math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
```

Available as `math.isclose` and `pytest.approx` in Python, `np.isclose` in NumPy. JS and Go have no builtin, so write the combined check explicitly.

The absolute term handles values near zero and the relative term handles large values. Pick tolerances from how much error the computation accumulates, not from habit.

## Catastrophic cancellation

The most dangerous failure, because it destroys precision silently. Subtracting nearly-equal numbers cancels the leading significant digits and promotes accumulated rounding error into the leading position. The digit count is unchanged, and almost none of them are still correct.

```python
>>> 1.0000000000000002 - 1.0000000000000000
2.220446049250313e-16      # one significant digit of real information
```

**Quadratic formula.** When `b² >> 4ac`, `-b + sqrt(b*b - 4*a*c)` cancels catastrophically:

```python
q = -(b + math.copysign(math.sqrt(b*b - 4*a*c), b)) / 2
x1, x2 = q / a, c / q
```

**Variance.** The textbook one-pass formula `E[x²] - E[x]²` subtracts two large nearly-equal numbers and can return a negative variance. Use Welford's algorithm:

```python
mean = m2 = 0.0
for i, x in enumerate(xs, 1):
    d = x - mean
    mean += d / i
    m2 += d * (x - mean)
variance = m2 / (len(xs) - 1)
```

Other stable rewrites: `log(1+x)` becomes `math.log1p(x)`, `exp(x)-1` becomes `math.expm1(x)`, `sqrt(x*x + y*y)` becomes `math.hypot(x, y)` which also avoids overflow, and `log(a)-log(b)` becomes `log(a/b)`.

General rule: rearrange to avoid subtracting nearly-equal quantities, and where that is impossible use a published stable algorithm.

## Summation error

Error grows with the number of terms:

```python
>>> sum([0.1] * 10_000_000)
999999.9998389754        # should be 1000000.0
>>> math.fsum([0.1] * 10_000_000)
1000000.0                # exactly rounded
```

`np.sum` uses pairwise summation, giving O(log n) error instead of O(n). Where no builtin exists, use Kahan compensated summation:

```python
total = c = 0.0
for x in xs:
    y = x - c
    t = total + y
    c = (t - total) - y
    total = t
```

Do not compile this with `-ffast-math`, which permits reassociation and deletes the compensation. Sorting by magnitude before summing also helps substantially.

## Special values

| Value | Surprising behavior |
|---|---|
| `NaN` | **`NaN != NaN`**. Test with `math.isnan()`. Any arithmetic with NaN yields NaN, so one NaN poisons a whole computation |
| `NaN` in containers | Sorting is undefined with NaN present, a `set` may hold two NaNs, and dict lookup by NaN key can fail |
| `-0.0` | `-0.0 == 0.0` is true, but `1/-0.0` is `-inf` and `1/0.0` is `+inf`. Detect with `math.copysign` |
| `inf` | `inf - inf` is NaN. Overflow produces `inf` silently, with no exception |
| Integers past 2⁵³ | `9007199254740993.0 == 9007199254740992.0`. **JavaScript numbers are doubles**, so an int64 ID sent as a JSON number is silently corrupted. Send IDs as strings |

That last row is a frequent production bug: a 64-bit database ID serialized as a JSON number arrives in a browser as a different ID.

## Where floats are correct

Floats are right for measurements, physics, graphics, statistics, and machine learning, where input is already approximate and relative error is what matters.

Use exact types when the value is counted rather than measured: money, quantities, IDs, and anything two systems must agree on exactly.

## Review checklist

1. Money, quantities, or IDs stored as floats, including in the DB schema and JSON contract?
2. `==` between floats, or a bare-epsilon comparison?
3. Subtraction of nearly-equal values: variance, differences of large sums, quadratic roots?
4. Long accumulation without `fsum`, pairwise, or Kahan?
5. NaN checked with `isnan` rather than `==`?
6. Int64 IDs crossing a JavaScript boundary as numbers rather than strings?
7. `-ffast-math` enabled in numerical code?
