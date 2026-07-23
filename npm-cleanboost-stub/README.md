# cleanboost (DEPRECATED stub)

> ⚠️ **This stub is deprecated.** The canonical CleanBoost package is
> published under the same `cleanboost` name from the [`npm-cli/`](../npm-cli/)
> directory in this monorepo. Install from there for the actual binary:
>
> ```bash
> npm install -g cleanboost@latest
> ```

## Why this stub exists

Originally, the npm package was published under a transliterated name so
existing installs kept working after a brand revision. A brand-canonical
alias stub depended on it to forward execution. After the full
normalization (this package is now `cleanboost` everywhere), the stub is
redundant and only kept for forward-compatibility with installs that may
still resolve to it transiently.

## What this stub does today

1. On install, prints a friendly deprecation notice (`scripts/postinstall.js`).
2. On execution (`bin/cleanboost.js`):
   - Searches `PATH` for a real `cleanboost` binary that is **not** this script.
   - If found, `execFile`s it transparently with the same argv.
   - Otherwise prints a one-line explanation and exits 0.

It has **no runtime dependencies** (the original self-referential dependency
on `cleanboost@3.1.1` would have caused a recursive install loop).

## License

MIT — see [`LICENSE`](LICENSE).
