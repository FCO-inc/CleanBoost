# CleanBoost

CleanBoost is software that runs in the **terminal**. **Fast**, **simple**, **100% free**. It detects installed games and cleans caches that slow down your system.

Runs on **macOS** and **Windows**. Zero dependencies. Zero telemetry. 100% local.

## What it does

**Detects:** CPU, RAM, GPU, disk specs. Detects installed games (Steam, Epic Games, Battle.net, GOG Galaxy, Minecraft, Roblox).

**Optimizes:** Clears shader caches (DirectX, NVIDIA, AMD on Windows; Steam shadercache on macOS).

**Cleans:** Recycle bin, temporary files, system cache.

## Install (one command, ~30 seconds)

### macOS / Linux

```bash
curl -sSL https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.ps1 | iex
```

### What happens, step by step

The installer runs these checks automatically:

| Step | What it does | Why |
|------|--------------|-----|
| **1** | Detect OS (macOS / Windows / Linux not supported) | CleanBoost needs the right paths for your machine |
| **2** | Check Python 3.8+ | Python is the runtime; minimum version is 3.8 |
| **3** | Check that `pip` is available | `pip` is the package installer Python uses |
| **4** | Download wheel from GitHub (5 kB) | Fetches the prebuilt package, ~1 second on broadband |
| **5** | Run `pip install --user` | Installs the `cleanboost` binary to your user site (`~/.local/bin` on macOS, `AppData\Roaming\Python\Scripts` on Windows) |
| **Verify** | Run `cleanboost --version` | Confirms `cleanboost 3.1.2` is installed and on PATH |

If anything fails, the installer prints the **exact command** to fix it.

## After install

```bash
cleanboost               # Interactive 3-button menu (with progress bar)
cleanboost --quick       # Run OPTIMIZE + CLEAN silently (no prompts)
cleanboost --enable-daemon   # Install weekly reminder service
cleanboost --version     # Print version (should be: cleanboost 3.1.2)
```

## What it does NOT do

- ❌ No cloud. No servers. No internet calls. Offline after install.
- ❌ No telemetry. No analytics. No tracking.
- ❌ No bundled malware. No bloatware.
- ❌ No subscription. No trial. No premium tier.

**100% free. 100% open source. 100% local. 100% offline.**

## Manual install (alternative)

If `curl | bash` is not for you, install from source:

```bash
git clone https://github.com/FCO-inc/CleanBoost.git
cd CleanBoost
python3 -m pip install --user dist/cleanboost-3.1.2-py3-none-any.whl
cleanboost --version
```

Or from PyPI once published:

```bash
python3 -m pip install --user cleanboost
```

## Requirements

- **Python 3.8+** (works with 3.8, 3.9, 3.10, 3.11, 3.12, 3.13)
- **`pip`** (usually bundled with Python)
- **`curl`** (ships with macOS and most Linux; Windows 10+ has it)
- **macOS** or **Windows** (Linux distributions manage caches natively)

If pip fails on a modern externally-managed Python (PEP 668):

```bash
python3 -m pip install --user --break-system-packages \
    https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/dist/cleanboost-3.1.2-py3-none-any.whl
```

## Uninstall

```bash
python3 -m pip uninstall cleanboost
```

No files left behind. The wheel installs to user site only.

## Source code

https://github.com/FCO-inc/CleanBoost

## License

MIT License. See [LICENSE](./LICENSE).
