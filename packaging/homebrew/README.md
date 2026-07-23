# Publishing CleanBoost to Homebrew

This guide publishes CleanBoost to a personal Homebrew **tap** so any macOS user can
install it with one command:

```bash
brew install FCO-inc/CleanBoost/cleanboost
```

## One-time setup

### 1 · Create the tap repository

GitHub → **New repository**:

| Field | Value |
|---|---|
| Owner | `Freebuff` |
| Name   | `homebrew-cleanboost` |
| Visibility | **Public** |
| Initialize | unchecked (no README/LICENSE; we ship them ourselves) |

Or via `gh`:

```bash
gh repo create FCO-inc/homebrew-cleanboost --public \
  --description "Homebrew tap for cleanboost" \
  --confirm
```

### 2 · Push the Formula into the tap

```bash
# Clone the empty tap repo
git clone https://github.com/FCO-inc/homebrew-cleanboost.git
cd homebrew-cleanboost
mkdir -p Formula
cp ../cleanboost/packaging/homebrew/cleanboost.rb Formula/cleanboost.rb

git add Formula/cleanboost.rb
git commit -m "Add cleanboost 3.1.1"
git push -u origin main
```

### 3 · (Optional) Submit to homebrew-core

If you prefer the user experience to skip the `tap` step:

```bash
gh repo fork Homebrew/homebrew-core --clone --remote
cp Formula/c/cleanboost.rb ../homebrew-core/Formula/c/cleanboost.rb
cd ../homebrew-core
git checkout -b cleanboost-3.1.1
git add Formula/c/cleanboost.rb
git commit -m "cleanboost 3.1.1 (new formula)"
gh pr create --fill
```

Expect strict review (1–7 days). The Formula must pass `brew audit --strict --new` and
`brew style`. Most personal taps skip this step.

## Validate locally before pushing

```bash
# Without a checkout-tap prefix brew won't run the full audit on a path.
# Use brew style + brew audit on the file directly:
brew style packaging/homebrew/cleanboost.rb
brew audit --strict --new packaging/homebrew/cleanboost.rb

# Functional check (will create a Cellar instance):
brew install --build-from-source packaging/homebrew/cleanboost.rb
cleanboost --version   # → cleanboost 3.1.1
brew uninstall cleanboost
```

## Update for a new version (e.g. 3.1.2)

1. Bump the version in `pyproject.toml` and `changelogs/…`.
2. Rebuild and upload to PyPI (`REPO=pypi PYPI_TOKEN=… bash scripts/publish_pypi.sh`).
3. Get the new sha256:
   ```bash
   curl -sSL https://files.pythonhosted.org/packages/source/c/cleanboost/cleanboost-3.1.2.tar.gz | shasum -a 256
   ```
4. Update `cleanboost.rb`: bump `url` + replace `sha256` with the new hash.
5. Commit & push to the tap.

Users get the new version on next `brew upgrade` (or `brew install --upgrade`).

## End-user installation

After the tap is live:

```bash
# Mac user, fresh shell:
brew install FCO-inc/CleanBoost/cleanboost
cleanboost --help
```
