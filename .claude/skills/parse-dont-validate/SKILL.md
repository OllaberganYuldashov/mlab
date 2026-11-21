---
name: parse-dont-validate
description: This skill should be used when the user asks "where should validation live", "how do I stop re-checking this everywhere", "how do I make illegal states unrepresentable", or when reviewing non-null assertions, casts, or repeated checks deep in the code, or designing a DTO whose optional fields are only valid in certain combinations.
---

# Parse, don't validate

Two functions can check the same condition and differ enormously in value:

```python
def validate_non_empty(xs: list[T]) -> None:              # validation
    if not xs: raise ValueError

def parse_non_empty(xs: list[T]) -> NonEmpty[T] | None:   # parsing
    return NonEmpty(xs[0], xs[1:]) if xs else None
```

The validator checks and discards the information. Every function downstream must re-check or hope. The parser checks and returns a value carrying the proof, so downstream code holding a `NonEmpty[T]` cannot be wrong about it and `head()` becomes total.

> Validation returns a boolean. Parsing returns a narrower type.

The distinction is Alexis King's, from 2019.

## The smell

```ts
function processOrder(order: Order) {
  if (!order.customerId) throw new Error("no customer");   // check
  chargeCustomer(order);
}

function chargeCustomer(order: Order) {
  const id = order.customerId!;    // claims a check in another file
}
```

Nothing enforces that assertion, and someone will add a second caller. Narrow the type instead:

```ts
type Order = { customerId?: string; /* ... */ }
type PlacedOrder = Order & { customerId: string }

function parseOrder(o: Order): PlacedOrder | null {
  return o.customerId ? (o as PlacedOrder) : null;
}

function chargeCustomer(order: PlacedOrder) {
  const id = order.customerId;   // total, no assertion, no re-check
}
```

## Shotgun parsing

The named anti-pattern from the LangSec work: interleaving validation with processing, so the program is partway through acting on input when it discovers the input was bad. Half-written rows, half-charged customers, half-sent emails.

Enforce a hard phase separation:

```
input -> [ parse: all checks, no effects ] -> valid value -> [ act: no checks, all effects ]
```

Any check appearing after the first side effect is shotgun parsing. This is the same shape as "functional core, imperative shell".

## Making illegal states unrepresentable

```ts
// {status:"success"} with no data typechecks
type Result = { status: "loading" | "success" | "error"; data?: User; error?: string }

// permits only the three real states
type Result =
  | { status: "loading" }
  | { status: "success"; data: User }
  | { status: "error"; error: string }
```

Four impossible states deleted, and `switch` on `status` now narrows automatically. Every defensive branch removed also lowers caller complexity. See `cyclomatic-complexity`.

Equivalent constructs: Rust `enum`, Python `match` on a tagged union, Kotlin and Java sealed types, Haskell and OCaml ADTs.

## Per-language recipes

| Language | Unforgeable type |
|---|---|
| **TypeScript** | Branded type: `type Email = string & { readonly __brand: unique symbol }`, constructed only by the parser. Or Zod, where `schema.parse()` returns the inferred narrow type |
| **Python** | `NewType("Email", str)` for a lightweight brand, Pydantic models for real edge parsing, frozen dataclasses validating in `__post_init__` |
| **Rust** | Newtype with a private field plus `Email::parse() -> Result<Email, _>`. Nothing outside the module can construct one |
| **Go** | Unexported field in an exported struct plus a `New...()` constructor in the same package. Design so the zero value is either valid or obviously unusable |
| **Java/Kotlin** | Private constructor plus a static factory returning `Optional` or `Result`, records for the parsed shape, sealed interfaces for state machines |

Two rules make any of these work:

1. **One construction path.** A second way to build the value removes the guarantee.
2. **Parse at the outermost edge**: HTTP handler, CLI arg parsing, queue consumer, DB row mapping.

## Where parsing belongs

```
HTTP handler        <- parse here: raw JSON to domain types
  service layer     <- already typed, no re-checking
    domain logic    <- total functions only
      repository    <- parse DB rows back into domain types
```

The database is an input boundary too. A fetched row is untrusted until parsed, because old rows were written by older code under weaker rules.

## Signs of validating where parsing belongs

- `!`, `as`, `unwrap()`, `cast()`, or `# type: ignore` below the boundary layer
- The same `if x is None` in three functions along one call path
- A docstring saying "assumes x has already been validated"
- A function taking broad types and immediately narrowing them
- `assert` used for business rules in the core
- A DTO with many optional fields where only certain combinations are legal

## When not to apply it

- **Scripts, or code with one call site.** The guarantee costs a type. One caller means a check is enough.
- **Languages with no way to restrict construction.** Phase separation still applies, but it yields discipline rather than enforcement. State that plainly in review rather than implying the newtype is airtight.
- **Boundaries not under control.** Parse what arrives and reject early with a clear error.

The related trap is parsing so strictly that valid input is rejected. Be strict about fields depended on, permissive about fields ignored. See `hyrums-law`.
