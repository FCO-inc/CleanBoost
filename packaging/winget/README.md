# Submitting CleanBoost to winget (Windows Package Manager)

This guide walks through the PR to `microsoft/winget-pkgs` so any Windows user can
install it with one command:

```powershell
winget install --id Freebuff.CleanBoost
```

## One-time setup

### 1 · Build & upload the Windows binary

The winget installer manifest points to a GitHub Release asset, so the **.zip must
exist first**. Two options:

**Option A — Push a tag and let GitHub Actions build it (recommended):**

```bash
git tag v3.1.1
git push --tags
# .github/workflows/release.yml runs:
#   macos-latest -> CleanBoost-3.1.1.dmg
#   windows-latest -> cleanboost-3.1.1-windows-x64.exe + .zip
# and uploads them to the v3.1.1 GitHub Release.
```

**Option B — Build locally on a Windows machine:**

```cmd
git clone https://github.com/FCO-inc/CleanBoost.git
cd cleanboost
git checkout v3.1.1
pip install pyinstaller
packaging\build_windows.bat
# Upload dist\cleanboost.exe to a GitHub Release as
#   cleanboost-3.1.1-windows-x64.zip  (zip the .exe!)
```

### 2 · Compute the SHA256 of the .zip asset

After the Release is published:

```bash
curl -sSL -L https://github.com/FCO-inc/CleanBoost/releases/download/v3.1.1/cleanboost-3.1.1-windows-x64.zip \
  | shasum -a 256
```

Copy the resulting hash into **both** manifests:

- `Freebuff.CleanBoost.yaml` → `InstallerSha256`
- `Freebuff.CleanBoost.installer.yaml` → `Installers[0].InstallerSha256`

### 3 · Fork `microsoft/winget-pkgs`

```bash
gh repo fork microsoft/winget-pkgs --clone --remote
cd winget-pkgs
```

### 4 · Stage the manifests

The path is **strict** — winget uses lowercase first letter of publisher, then case-sensitive:

```
manifests/f/Freebuff/CleanBoost/3.1.1/
  ├── Freebuff.CleanBoost.yaml
  ├── Freebuff.CleanBoost.installer.yaml
  └── Freebuff.CleanBoost.locale.en-US.yaml
```

The 3 files already live at exactly this path inside this repo:

```
cleanboost/packaging/winget/manifests/f/Freebuff/CleanBoost/3.1.1/
```

Copy that whole directory into your fork:

```bash
mkdir -p manifests/f/Freebuff/CleanBoost/3.1.1
cp ../cleanboost/packaging/winget/manifests/f/Freebuff/CleanBoost/3.1.1/*.yaml \
   manifests/f/Freebuff/CleanBoost/3.1.1/
```

### 5 · Validate manifests locally

```powershell
# Install wingetcreate (Microsoft's official helper):
winget install Microsoft.WingetCreate

# Validate:
wingetcreate validate `
  --manifest manifests/f/Freebuff/CleanBoost/3.1.1/Freebuff.CleanBoost.yaml
```

If `wingetcreate` is unavailable, use the schema validator:

```bash
pip install winget-pkgs-validator
winget-pkgs-validator validate . \
  -p manifests/f/Freebuff/CleanBoost/3.1.1/Freebuff.CleanBoost.yaml
```

### 6 · Submit PR

```bash
git checkout -b new-Freebuff-CleanBoost-3.1.1
git add manifests/f/Freebuff/CleanBoost/3.1.1/
git commit -m "New: Freebuff.CleanBoost version 3.1.1"
git push origin HEAD

# Then open a PR via GitHub UI (gh repo view opens in browser) or:
gh pr create --fill \
  --title "New package: Freebuff.CleanBoost version 3.1.1" \
  --body "Automated submission via wingetcreate / manually authored manifests. See manifest contents for details."
```

### 7 · Wait for the winget bot reviewer

Typical turnaround: **1–7 days**. The PR includes an automated validation bot plus
a human reviewer.

## After merge

```powershell
winget install --id Freebuff.CleanBoost
cleanboost --version   # → cleanboost 3.1.1
```

## For a new version (3.1.2, …)

1. Bump version in `pyproject.toml`.
2. Tag & push (`git tag v3.1.2 && git push --tags`) — CI publishes new GitHub Release.
3. Update the 3 manifest files:
   - Bump `PackageVersion`
   - Update `ReleaseDate`
   - Update `ReleaseNotes`/`ReleaseNotesUrl`
   - Replace `InstallerSha256` with the new zip hash
4. Stage them under `manifests/f/Freebuff/CleanBoost/<new-version>/` (different folder).
5. Open new PR.
