---
name: unicode-pitfalls
description: This skill should be used when the user asks "why is this string length wrong", "how do I truncate text safely", "why do these identical strings not match", "how do I compare text case-insensitively", "why does emoji break my column limit", or is handling normalization, encodings, grapheme clusters, or homoglyph attacks.
---

# Unicode pitfalls

## Length has three meanings

For "👨‍👩‍👧‍👦" (family emoji):

| Measure | Value | Use for |
|---|---|---|
| Bytes (UTF-8) | 25 | Storage limits, network buffers |
| Code points | 7 | Almost never |
| Grapheme clusters | 1 | Anything a user sees or counts |

`len()` in Python and `.length` in JS give code points (JS gives UTF-16 units, so emoji count as 2). Neither matches what a user calls a character.

```python
import regex
len(regex.findall(r'\X', s))     # grapheme clusters
```

| Language | Grapheme-aware |
|---|---|
| Python | `regex` module, `\X` |
| JS | `Intl.Segmenter(locale, {granularity:'grapheme'})` |
| Rust | `unicode-segmentation` crate |
| Swift | `String.count` is already grapheme-based |
| Go | `rivo/uniseg` |

## Never slice by index

`s[:20]` can cut a multi-byte character in half, split an emoji from its modifier, or separate a base character from its combining accent. Result is mojibake or a different character.

Truncate on grapheme boundaries:

```python
import regex
def truncate(s, n):
    g = regex.findall(r'\X', s)
    return ''.join(g[:n]) + ('…' if len(g) > n else '')
```

For a byte limit (DB column, protocol field), cut on a character boundary at or below the limit, not at the exact byte.

## Normalization

The same visible text has multiple valid encodings. "é" is either U+00E9 (composed) or U+0065 U+0301 (e + combining accent). They render identically and compare unequal.

```python
import unicodedata
a = "café"                    # composed
b = "café"              # decomposed
a == b                        # False
unicodedata.normalize('NFC', a) == unicodedata.normalize('NFC', b)   # True
```

| Form | Meaning | Use |
|---|---|---|
| **NFC** | Composed. Shortest form. | Default for storage and comparison |
| NFD | Decomposed | Sorting, accent stripping |
| NFKC | Composed + compatibility folding ("ﬁ"→"fi", "①"→"1") | Identifiers, search |
| NFKD | Decomposed + compatibility | Search indexing |

Rules:

1. Normalize to **NFC at the input boundary**, once. Store normalized.
2. Never compare unnormalized strings for equality or uniqueness.
3. macOS filesystems produce NFD while most other sources produce NFC. A file synced between systems then has two names that look identical.

NFKC loses information ("²" becomes "2"), so use it for matching, not for storage of display text.

## Case folding, not uppercasing

`upper()` is for display. `casefold()` is for comparison.

```python
"ß".upper()      # 'SS'
"ß".lower()      # 'ß'   round trip is lossy
"ß".casefold()   # 'ss'  matches "SS" correctly
```

The Turkish dotless i is the classic production bug:

```python
"I".lower()                        # 'i'   in most locales
# in tr_TR locale, "I".lower() is 'ı' (dotless)
```

Any code doing `s.lower() == "identifier"` under a Turkish locale compares wrong. This has broken installers, config parsers, and auth checks.

Rules:

- Compare with `casefold()` (Python), `toLowerCase()` with an explicit `'en-US'` locale in JS, or `ToLowerInvariant()` in .NET.
- Never use locale-dependent case conversion for protocol tokens, filenames, or keys.
- Normalize before folding: `unicodedata.normalize('NFC', s).casefold()`.

## Homoglyphs and identifiers

"раypal.com" with Cyrillic "р" and "а" looks identical to "paypal.com". For anything that identifies a user or resource:

- Apply NFKC.
- Restrict to a script allowlist, or reject mixed-script strings.
- Reject zero-width characters (U+200B-200D, U+FEFF) and bidi controls (U+202A-202E, U+2066-2069). Bidi controls can make displayed source code differ from what compiles (the "Trojan Source" attack).
- Compare against existing entries after normalization plus confusable-skeleton mapping (UTS 39).

## Encoding hygiene

- **Always specify the encoding.** `open(path)` uses a platform default that differs between machines. Use `encoding='utf-8'`, and set `PYTHONUTF8=1`.
- **UTF-8 everywhere**, including the DB (`utf8mb4` in MySQL, not `utf8`, which is 3-byte and cannot store emoji), the connection charset, and the HTTP `Content-Type`.
- **Handle the BOM.** Excel writes UTF-8 with a BOM. Read with `utf-8-sig` to strip it.
- **Decide the error policy explicitly**: `strict` for trusted data, `replace` for display, never silent.

## Emails and identifiers

Do not validate emails with a regex or normalize the local part. `User@example.com` and `user@example.com` may be different mailboxes, since only the domain is case-insensitive. Lowercase the domain, leave the local part alone, and verify by sending mail.

## Checklist

1. Truncation and slicing on grapheme boundaries, not indexes
2. NFC normalization at every input boundary
3. `casefold()` for comparison, never locale-dependent `lower()`
4. Length limits stated as bytes or graphemes, and enforced as the same one
5. Explicit `utf-8` on every file, socket, and DB connection
6. `utf8mb4` in MySQL
7. Zero-width and bidi characters rejected in identifiers
