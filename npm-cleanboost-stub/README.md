# `cleanboost` (npm)

> Brand-canonical npm alias for the [`cleenboost`](https://www.npmjs.com/package/cleenboost)
> package. Both install names produce the same `cleanboost` binary on your
> `PATH`.

This package is a **thin alias**, not a re-implementation. It exists so
that the install command matches the brand:

```bash
npm install -g cleanboost   # ← brand-canonical, preferred
# or, equivalently:
npm install -g cleenboost   # ← legacy package name (back-compat)
```

Either command ends with a working `cleanboost`, `cleanboost-cli`, or `cb`
executable on your shell `PATH`, and downloads the same prebuilt
single-binary release of CleanBoost from
[GitHub Releases](https://github.com/Freebuff/cleanboost/releases/tag/v3.1.1).

## What's inside

```
npm-cleanboost-stub/
├── package.json         # name=cleanboost, dep=cleenboost@3.1.1, bin=cleanboost
├── bin/cleanboost.js    # tiny shim: forwards to cleenboost/bin/cleanboost.js
├── scripts/postinstall.js # friendly confirmation message after install
├── README.md
└── LICENSE              # MIT (same as parent repo)
```

The `bin/cleanboost.js` shim is deliberately minimal:

```js
require('cleenboost/bin/cleanboost.js');
```

That's it. All of CleanBoost's actual behavior — cache detection, the
interactive menu, the `--quick` cron-friendly flag, the opt-in weekly
daemon — lives in the [`cleenboost`](https://www.npmjs.com/package/cleenboost)
package, and this stub asks Node to resolve and run it.

## Why does this exist?

CleanBoost is published under the legacy name `cleenboost` on PyPI and
npm to preserve upgrade compatibility for existing users (you can't
rename a package on those registries without breaking `pip install --upgrade`
and `npm update` flows). The brand, however, is **`cleanboost`** — and we
want the install command a new user types to be the brand-canonical
name, not the legacy spelling.

- **pip** (PyPI): no aliasing mechanism. Users must use `pip install --user cleenboost`.
- **winget / Homebrew**: same — naming is locked by the package identifier /
  formula filename.
- **npm**: supports aliasing via dependency redirect, which is what this
  package does. After installing it, `cleanboost` works *as if* npm had
  a package under that name.

## Install

```bash
npm install -g cleanboost
```

That's it. Behind the scenes:

1. npm downloads `cleanboost` from the registry.
2. npm sees the `cleenboost` dependency in this package's `package.json`
   and installs `cleenboost@3.1.1` into `cleanboost`'s nested
   `node_modules`.
3. npm processes the bin declaration in this package's `package.json`
   and creates symlinks for `cleanboost`, `cleanboost-cli`, and `cb`
   in your global prefix bin directory.
4. `cleenboost`'s own postinstall downloads the prebuilt Python binary
   from GitHub Releases and installs it to `~/.cleanboost/bin/cleanboost`.
5. Final postinstall of THIS package prints a confirmation.

If you already had `cleenboost` installed globally, npm's global bin
symlink will be overwritten by this stub's bin script (which forward-execs
to cleenboost). The end-user behaviour is identical — just the symlink
points into the stub's tree. To restore the original symlink, `npm
uninstall -g cleanboost` and `npm install -g cleenboost` again.

## Publishing

This package is published from the same Git repository as the rest of
CleanBoost. The publishing sequence is:

```bash
# 1. Verify the name is still free (optional but recommended)
npm view cleanboost        # should 404 the first time

# 2. Publish the real package first (so the stub's dependency resolves)
cd ../npm-cli && npm publish --access public

# 3. Publish the stub (depends on cleenboost by exact version "3.1.1")
cd ../npm-cleanboost-stub && npm publish --access public
```

When bumping CleanBoost to a new version (e.g. `3.1.2`), bump the version
in **both** `npm-cli/package.json` AND `npm-cleanboost-stub/package.json`,
and bump the exact dependency version in the stub from `"3.1.1"` to
`"3.1.2"`. Publish `npm-cli` first, then the stub, so the dependency
becomes resolvable on the registry by the time npm processes the stub.

## License

MIT — same as the [parent repository](https://github.com/Freebuff/cleanboost).
See the `LICENSE` file at this directory and at the repo root.
