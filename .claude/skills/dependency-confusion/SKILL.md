---
name: dependency-confusion
description: This skill should be used when the user asks "how do I secure our package supply chain", "what is dependency confusion", "how do I stop typosquatting", "is this package safe to install", "should I pin dependency hashes", or is configuring a private registry, lockfile policy, or CI credentials for package installs.
---

# Supply chain: dependency confusion and friends

## Dependency confusion

Disclosed by Alex Birsan in 2021, and it worked against Apple, Microsoft, PayPal, Tesla, and Shopify simultaneously.

Most package managers configured with both a private registry and the public one resolve a name by asking **both** and taking the **highest version**. An attacker publishes `your-internal-package-name` publicly at version `99.0.0`, and every build resolving that name installs the attacker's code. No misconfiguration is required beyond the default resolution order.

Internal names are not secret. They leak through published manifests, source maps, Docker layers, CI logs, job postings, and code search.

### Fixes by ecosystem

| Ecosystem | Control |
|---|---|
| **npm** | **Scope everything** as `@yourorg/pkg` and claim the scope publicly, then map the scope to the private registry in `.npmrc`. Strongest fix, since a scope is a namespace nobody else can publish under |
| **npm, alternative** | One upstream that proxies public packages, never two registries able to answer for the same name |
| **Python** | Never use `--extra-index-url`, which is exactly the ambiguous-resolution setting. Use `--index-url` against one proxying repository. Pip has no scoping |
| **Go** | `GOPRIVATE` and `GONOSUMDB` for internal prefixes. Module paths are already domain-scoped |
| **Maven** | Configure the private repo as a mirror of everything, not an additional repository |
| **Ruby** | Per-gem `source` blocks in the Gemfile |

The general rule: **one resolution source**. Any configuration where two registries can answer for one name is exploitable, because the tiebreak is version-based, not source-based.

Defensively registering internal names publicly is a stopgap. It does not scale and fails for every name added later.

## Typosquatting and slopsquatting

**Typosquatting**: `reqeusts`, `crossenv` versus `cross-env`. Install scripts then run arbitrary code.

**Slopsquatting** is the newer variant: language models hallucinate plausible package names, and attackers register the frequently hallucinated ones. Any package name suggested by a model or by autocomplete requires verification before entering a manifest.

Verify a new dependency by checking:

1. The repository link resolves and matches the package name.
2. Download counts and publication history. Twenty downloads and one version published last week warrants scrutiny.
3. The maintainer list against the project's actual maintainers.
4. Whether install scripts exist (`preinstall`, `postinstall`, code executing in `setup.py`).
5. Whether the package is even needed, since a small dependency is often worse than ten lines of code.

## Lockfiles and pinning

- **Commit the lockfile.** Without it, resolution is a function of when the build ran.
- **Install with the lockfile-respecting command**: `npm ci` rather than `npm install`, `uv sync` or `pip-sync` rather than `pip install -r`. Regular install commands silently update the lockfile.
- **Pin with hashes** where supported: `pip install --require-hashes`, npm integrity fields, Go's `go.sum`. A version identifies a name, a hash identifies content, and only the hash survives a compromised registry or a republished version.
- **Review lockfile diffs.** An unexpected transitive change in a PR that touched no dependencies is worth reading.

## Other vectors

| Vector | Defense |
|---|---|
| **Maintainer account takeover** | Hash pinning, delayed adoption (skip versions published in the last 24 to 48 hours), advisory monitoring |
| **Malicious install scripts** | `--ignore-scripts` by default, build in a sandbox with no network and no credentials |
| **CI credential theft** | Never expose publish tokens or cloud credentials to a step running third-party code. Separate install from deploy |
| **Compromised build system** | Reproducible builds and provenance attestation (SLSA, npm provenance, Sigstore) |
| **Package deletion or protestware** | Vendor critical dependencies, or run an internal proxy caching every version fetched |
| **Git dependency on a mutable ref** | Pin to a commit SHA, never a branch or tag, since tags can be moved |

## Configuration

```bash
npm config set ignore-scripts true
```

```ini
# .npmrc scoped to the private registry only
@yourorg:registry=https://registry.internal.example.com
//registry.internal.example.com/:_authToken=${NPM_TOKEN}
```

```
# Python: one index, hashes required
--index-url https://pypi.internal.example.com/simple
--require-hashes
```

## Audit checklist

1. **Can any internal package name resolve from a public registry?** This is the dependency confusion test and the answer must be no.
2. Are internal npm packages scoped, with the scope claimed publicly?
3. Does `--extra-index-url` appear anywhere in Python config or Dockerfiles?
4. Does CI install with a lockfile-respecting command?
5. Do install scripts run, and does that step hold credentials or network access?
6. Are git dependencies pinned to commit SHAs?
7. Are hashes required, or only version numbers?

Item 1 is the one to check immediately. It has a definite answer, and a "yes" is a live vulnerability rather than a theoretical one.
