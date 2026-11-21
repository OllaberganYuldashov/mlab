---
name: cyclomatic-complexity
description: This skill should be used when the user asks "how complex is this function", "count the branches", "find overly complex functions", "set a complexity threshold", "reduce cyclomatic complexity", or asks to interpret a complexity report from radon, ESLint, gocyclo, PMD, or lizard. Also applies when a function "has too many if statements" and needs simplifying.
---

# Cyclomatic complexity

Cyclomatic complexity counts the independent paths through a function. It estimates two things: the minimum number of test cases needed for branch coverage, and how much a reader must hold in mind at once.

## Counting rule

Start at 1. Add 1 for each decision point.

| Add 1 for | Notes |
|---|---|
| `if`, `else if` | `else` adds nothing, it is the fall-through path |
| `for`, `while`, `do-while` | each loop |
| `case` in a `switch` | each case label. The `switch` and `default` add nothing |
| `catch` / `except` | each handler. `try` and `finally` add nothing |
| `&&`, `\|\|`, `??` | each short-circuit operator |
| ternary `? :` | one each |
| `?.` optional chaining | one each, though some tools skip it |
| pattern-match arm with a condition | each arm |

Nothing else counts. Assignments, calls, returns, and straight-line statements are free.

### Worked example

```python
def classify(user, order):          # 1  base
    if user is None:                # 2
        return "anonymous"
    if order.total > 100 and user.is_member:   # 3 if, 4 and
        return "vip"
    for item in order.items:        # 5
        if item.flagged:            # 6
            return "review"
    return "standard"
```

Complexity 6, so 6 test cases for full branch coverage.

## Interpreting the score

| Score | Band | Action |
|---|---|---|
| 1-5 | Simple | None |
| 6-10 | Moderate | Acceptable, monitor |
| 11-20 | Complex | Refactor when next touching it |
| 21-50 | High risk | Refactor now, hard to test fully |
| 50+ | Untestable | Redesign |

Gate CI at 10 per function if a single threshold is needed. Apply it consistently rather than debating case by case.

Two constraints on interpretation:

- The metric is per function, never per file. A large file of simple functions is fine.
- Parsers, state machines, and generated code score high legitimately. Exclude them rather than distorting code to satisfy a linter.

## Reducing it

Removing decision points lowers complexity. Moving them elsewhere does not. Splitting a complexity-20 function into two complexity-10 functions helps only when each half is independently understandable.

**Guard clauses.** Flatten nesting by returning early. The count is unchanged but nesting depth and cognitive load drop sharply.

```js
function pay(user) {
  if (!user) return null;
  if (!user.active) return null;
  if (user.balance <= 0) return null;
  return charge(user);
}
```

**Table lookup.** Replace an if/else chain that maps values to results. This genuinely removes branches.

```js
// complexity 5
function rate(tier) {
  if (tier === "free") return 0;
  if (tier === "pro") return 10;
  if (tier === "team") return 25;
  return 100;
}

// complexity 1
const RATES = { free: 0, pro: 10, team: 25 };
const rate = (tier) => RATES[tier] ?? 100;
```

**Extract a named predicate.** Move a compound condition into its own function. The operators still cost 1 each but now live in a small, separately testable unit.

**Polymorphism.** When the same `switch` on a type appears in several functions, move each branch onto the type.

**Split by responsibility.** A function that validates, transforms, and persists is three functions. This is the only refactor that reliably lowers the total complexity a reader absorbs at once.

**Define errors out of existence.** Every failure mode removed from a callee deletes a branch from every call site.

## Tooling

| Language | Tool | Command |
|---|---|---|
| Python | radon | `radon cc -s -n C path/` |
| JS/TS | ESLint | `"complexity": ["error", 10]` |
| Go | gocyclo | `gocyclo -over 10 .` |
| Java | PMD | `CyclomaticComplexity` rule |
| C/C++ and many others | lizard | `lizard -C 10 path/` |
| Multi-language | SonarQube | reports cyclomatic and cognitive complexity |

## Cognitive complexity

Cyclomatic complexity scores ten flat `if` statements the same as ten nested ones. Cognitive complexity (SonarSource, 2017) adds a nesting penalty and does not charge for a `switch`.

Use cyclomatic complexity to estimate test count, cognitive complexity to judge readability. When a tool reports both, gate CI on cyclomatic and use cognitive as the refactoring signal.

## Limits

The score says nothing about naming, coupling, duplication, or correctness. A complexity-3 function can be entirely wrong. Treat a high score as a candidate for review, not a verdict.

To decide which complex code is worth fixing, cross the score with change frequency using `code-hotspots`. To explain why a change is hard rather than why a function is hard to test, use `connascence`.
