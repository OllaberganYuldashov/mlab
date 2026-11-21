---
name: module-depth
description: This skill should be used when the user asks "should I split this class", "is this abstraction worth it", "why does this change ripple through so many layers", "is this wrapper useful", or when reviewing a new interface, wrapper, or layer. Applies Ousterhout's deep-versus-shallow module test, including when Clean Code's small-functions advice does not apply. Covers whether an abstraction earns its interface. For where validation belongs use `parse-dont-validate`.
---

# Module depth

Every module has two sides, and its worth is the gap between them.

- **Interface**: everything a caller must know. Not just signatures, but exceptions, required ordering, side effects, config read, and errors to handle.
- **Implementation**: everything it does.

A module's value is functionality hidden minus interface cost.

> A **deep** module has a small interface and substantial functionality behind it.
> A **shallow** module has an interface nearly as complex as its implementation, so it costs more to learn than it saves.

The framing is John Ousterhout's, from *A Philosophy of Software Design*. Unix file I/O is the canonical deep module: `open`, `read`, `write`, `close`, `lseek` hide disk scheduling, buffering, permissions, block allocation, device drivers, and the difference between a file, a pipe, and a socket.

## Why this outranks "keep it small"

Advice to write small classes and small functions optimizes only the implementation side. Applied without the cost side it produces **classitis**: many tiny classes, each simple, with the complexity relocated into the relationships between them and thirty interfaces to learn instead of three.

Reconcile the two rules this way:

- Split when the pieces have genuinely separate interfaces and a caller needs only one of them.
- Do not split when the pieces are only usable together, since that adds an interface and hides nothing.

Test after any proposed split: can either half be understood and used without reading the other? If not, the split made things worse.

## Red flags

### Pass-through methods

A method whose body calls a method with the same signature one layer down.

```java
public void charge(Card c, Money m) {
    processor.charge(c, m);       // adds interface, hides nothing
}
```

Fix by exposing the lower layer directly, merging the layers, or making the wrapper do real work such as retries, validation, or translation into domain terms. One thin adapter at a boundary owned for testing or vendor-swap reasons is a real if small benefit. Three stacked adapters are not.

### Pass-through variables

A parameter threaded through five functions because only the fifth uses it. Every function in the chain now carries that concept in its interface. Fix with a context object, dependency injection, or module-level state, each of which has costs, so choose deliberately.

### Information leakage

The same design decision reflected in more than one module. This is the deepest form of coupling and the one worth hunting.

When both `FileReader` and `FileWriter` know the header layout, a format change touches both. Fix by making one module own the format, with reading and writing inside it.

Leakage usually comes from **temporal decomposition**: splitting modules by when things happen (read, then process, then write) instead of by what knowledge they hold. Order of operations is the wrong axis, because the same knowledge is needed at several times.

### Interfaces that mirror implementation

An interface with one method per internal step is a to-do list, not an abstraction. Callers must sequence the steps correctly, which adds connascence of execution order on top of a shallow interface. See `connascence`.

## Define errors out of existence

The most reliable way to deepen a module is to reduce the number of ways it can fail.

| Design that throws | Design that does not |
|---|---|
| `substring()` throws on out-of-range indices | Python slicing clamps: `xs[2:99]` returns what exists |
| `delete` fails if the file is open (Windows) | Unix unlinks the name, the file goes when the last handle closes |
| `unset` errors when the variable is absent | Define "remove it" as "ensure it is gone" |
| Map lookup throws on a missing key | Return a default or an explicit optional |

Do not define away errors that matter: a failed payment must surface. Target incidental errors, where the caller's only sane response is to ignore it or do the obvious thing. Each one removed deletes a branch from every call site, lowering caller complexity too. See `cyclomatic-complexity`.

## Review checklist

1. Write the interface out in full: signatures, errors, ordering rules, config, side effects. A long list means a shallow module regardless of how clean the code is.
2. Name what a caller can now stop knowing. "Nothing, it is just organized differently" means this is not an abstraction.
3. Confirm each layer changes the level of abstraction. A layer speaking the same vocabulary as the one below is a pass-through in disguise.
4. Check whether any design decision is now written in two places.
5. Ask explicitly whether this could be one module instead of three. Review bias runs the other way.
6. Check the name. `Utils`, `Manager`, `Helper`, and `Service` usually mark a module with no coherent secret to hide.

## Somewhat general-purpose

Prefer interfaces slightly more general than today's need, with special cases layered above.

A text editor exposing `insert(text, pos)` and `delete(start, end)` is both simpler and more capable than one exposing `backspace()`, `deleteSelection()`, and `deleteWord()`. The general interface is smaller, and each special case becomes a short function on top.

This is not speculative generality. No unused features are added. A smaller, more fundamental interface is chosen for functionality already required.

## When to apply it

At design and code review, before the interface ships. Retrofitting depth means changing every call site, which is exactly the cost the metric predicts.
