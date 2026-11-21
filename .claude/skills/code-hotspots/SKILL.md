---
name: code-hotspots
description: This skill should be used when the user asks "where should we start refactoring", "which files are riskiest", "what is our tech debt priority", "which files always change together", "what is the bus factor", or asks to mine git history for code health signals. Combines change frequency with complexity to rank refactoring candidates.
---

# Code hotspots

Complexity costs money only in code that changes. A gnarly file untouched for four years costs nothing. A moderately complex file edited twice a week absorbs the bugs and the time.

So the ranking signal is not complexity:

> hotspot = change frequency x complexity

Git already recorded which code is hard, for free. Every commit to a file is evidence that somebody had to understand it. This is behavioral code analysis, from Adam Tornhill's *Your Code as a Crime Scene*.

## Step 1: change frequency

```bash
git log --format=format: --name-only --since=12.months \
  -- ':!*lock*' ':!*generated*' ':!vendor/*' ':!*.snap' \
  | sed '/^$/d' | sort | uniq -c | sort -rn | head -25
```

Use a 6 to 12 month window, matching how far back the team remembers. Longer windows include code that has since stabilized. Exclude lockfiles, generated code, vendored directories, and snapshots.

## Step 2: cross with complexity

Churn alone over-ranks config files and routers. Multiply by size or complexity:

```bash
git log --format=format: --name-only --since=12.months | sed '/^$/d' | sort | uniq -c | sort -rn | head -50 \
  | while read count file; do
      [ -f "$file" ] && echo "$((count * $(wc -l < "$file"))) $count $file"
    done | sort -rn | head -20
```

For a real complexity term, feed the top churned files to a complexity tool such as `radon cc -s` or `lizard --sort cyclomatic_complexity`. See `cyclomatic-complexity`.

The top five of that list is the refactoring backlog. Five files, not the codebase.

## Step 3: change coupling

Files that keep changing in the same commit are coupled even when nothing in the code says so. This finds what static analysis cannot: a client and server that must ship together, or two "independent" services sharing an implicit contract.

```bash
git log --format='%H' --name-only --since=12.months \
  | awk '/^[0-9a-f]{40}$/{c=$0; next} NF{print c" "$0}' \
  | awk '{a[$1]=a[$1]" "$2} END{for(c in a) print a[c]}' \
  | awk '{for(i=1;i<=NF;i++)for(j=i+1;j<=NF;j++) print ($i<$j? $i" "$j : $j" "$i)}' \
  | sort | uniq -c | sort -rn | head -20
```

Read results as questions:

- Source plus its own test: healthy, ignore
- Two modules in different packages coupled 80% of the time: a missing abstraction, or a boundary in the wrong place
- One file coupled to many unrelated files: a god object or a shared config

## Step 4: bus factor

```bash
git log --format='%an' --since=24.months -- path/to/file | sort | uniq -c | sort -rn
```

A hotspot with a bus factor of 1 is the highest-risk combination available: complex, constantly changing, and understood by one person. Escalate that combination rather than the raw complexity score.

## Reading the grid

| | Low churn | High churn |
|---|---|---|
| **Low complexity** | Healthy, leave it | Healthy but busy, check it is not accumulating responsibilities |
| **High complexity** | Dormant. Do not refactor for its own sake: no return, and real risk of breaking something nobody remembers | **Hotspot.** This is the entire list |

The most valuable output of this analysis is permission to skip the bottom-left quadrant.

## Keep blame honest

Bulk reformatting and renames destroy the signal. Record them so tooling skips them:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

One commit SHA per line. GitHub honors this file automatically.

## Tools

| Tool | Purpose |
|---|---|
| `code-maat` | Tornhill's CLI: churn, coupling, ownership, age from a git log export |
| CodeScene | Hosted equivalent with trend lines |
| `git-of-theseus` | Plots how much code from each year survives |
| `hercules` | Fast history analysis including code-age burndown |

## Limits

- Churn is not badness. An actively developed feature legitimately churns. This finds candidates, not defects.
- Splitting a hotspot into three files improves the metric without necessarily improving the code. Verify each piece is independently understandable. See `module-depth`.
- Never publish an ownership map as a performance metric. It measures who touched code, not who contributed, and becomes meaningless the moment it becomes a target.
