#!/usr/bin/env bash
# ==============================================================================
# CleanBoost v3.1.2 Installer — single-command via curl | bash
# ==============================================================================
# CleanBoost is software that runs in the terminal: fast, simple, 100% free.
# It detects installed games (Steam, Epic, Battle.net, GOG, Minecraft, Roblox)
# and optimizes caches. 100% local. 100% offline. Zero telemetry.
#
# Usage from any machine with curl + bash:
#   curl -sSL https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.sh | bash
#
# Requirements: Python 3.8+ with pip. macOS or Windows.
# Linux is NOT supported (Linux distributions manage caches natively).
# ==============================================================================

# ----------------------------------------------------------------
# BUMP THIS VERSION ON EVERY RELEASE.
# Also bump in pyproject.toml and main.py.
# ----------------------------------------------------------------
VERSION="3.1.2"
REPO_RAW_URL="https://raw.githubusercontent.com/FCO-inc/CleanBoost/main"
ARCHIVE_URL="https://github.com/FCO-inc/CleanBoost/archive/refs/heads/main.tar.gz"

set -euo pipefail
export LC_ALL=C

# Colors (only on TTY)
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ -n "${TERM:-}" ] && [ "${TERM:-}" != "dumb" ]; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BLUE=$(tput setaf 4)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BLUE="" BOLD="" RESET=""
fi

# ============================================================================
# Welcome banner
# ============================================================================
echo ""
echo "${BOLD}════════════════════════════════════════════════════════════════${RESET}"
echo "${BOLD}   CleanBoost v${VERSION} Installer${RESET}"
echo "${BOLD}   CleanBoost is fast, simple, 100% free terminal software.${RESET}"
echo "${BOLD}   Detects games. Optimizes caches. 100% local.${RESET}"
echo "${BOLD}════════════════════════════════════════════════════════════════${RESET}"
echo ""

# ============================================================================
# STEP 1 of 5: Detect your operating system
# ----------------------------------------------------------------------------
# CleanBoost supports macOS and Windows.
# Linux is not supported because Linux distributions manage caches natively.
# ============================================================================
echo "${BOLD}─── STEP 1 of 5: Detect your operating system ───${RESET}"
echo "  CleanBoost runs on macOS and Windows."
echo "  Linux is not supported because distributions manage caches natively."
echo ""

OS_RAW="$(uname -s 2>/dev/null || echo unknown)"
echo "  → Detected: ${BOLD}${OS_RAW}${RESET}"

case "$OS_RAW" in
    Darwin)
        OS="macos"
        echo "${GREEN}  ✓ macOS detected — CleanBoost is ready to install.${RESET}"
        ;;
    MINGW*|CYGWIN*|MSYS*|Windows_NT)
        OS="windows"
        echo "${GREEN}  ✓ Windows detected — CleanBoost is ready to install.${RESET}"
        echo ""
        echo "${BLUE}  Note: this is the bash version. For native Windows PowerShell,${RESET}"
        echo "${BLUE}  use install.ps1 from https://github.com/FCO-inc/CleanBoost.${RESET}"
        ;;
    Linux)
        echo "${BLUE}  ✗ Linux detected. CleanBoost does not support Linux.${RESET}"
        echo "${BLUE}  Linux distributions manage caches natively. Goodbye.${RESET}"
        exit 0
        ;;
    *)
        echo "${BLUE}  ✗ Unknown OS: ${OS_RAW}. CleanBoost cannot install here.${RESET}"
        exit 1
        ;;
esac
echo ""

# ============================================================================
# STEP 2 of 5: Verify Python 3.8 or newer is installed
# ----------------------------------------------------------------------------
# CleanBoost needs Python 3.8 or newer (works with 3.8, 3.9, 3.10, 3.11, 3.12, 3.13).
# CleanBoost has ZERO external dependencies — only the Python standard library.
# ============================================================================
echo "${BOLD}─── STEP 2 of 5: Verify Python 3.8 or newer is installed ───${RESET}"
echo "  CleanBoost needs Python 3.8 or newer."
echo "  CleanBoost has ZERO external dependencies — only Python standard library."
echo ""

if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "${RED}  ✗ Python is not installed.${RESET}"
    echo "  Please install Python 3.8+ from https://www.python.org/downloads/"
    echo "  Then re-run: curl -sSL https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.sh | bash"
    exit 1
fi

PY_VERSION="$($PY_BIN --version 2>&1 | head -1)"
echo "  → Found: ${BOLD}${PY_VERSION}${RESET}"

if ! $PY_BIN -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "${RED}  ✗ Python is too old. CleanBoost needs 3.8 or newer.${RESET}"
    echo "  You have: $PY_VERSION"
    echo "  Install a newer version from https://www.python.org/downloads/"
    exit 1
fi
echo "${GREEN}  ✓ Python version OK (3.8+)${RESET}"
echo ""

# ============================================================================
# STEP 3 of 5: Verify pip is available
# ----------------------------------------------------------------------------
# pip is the package installer for Python. We need it to install CleanBoost.
# If missing, try ensurepip; if that fails, the user needs system pip install.
# ============================================================================
echo "${BOLD}─── STEP 3 of 5: Verify pip is available ───${RESET}"
echo "  pip is the package installer for Python. We need it to install CleanBoost."
echo ""

if ! $PY_BIN -m pip --version >/dev/null 2>&1; then
    echo "${YELLOW}  pip not detected. Attempting ensurepip --default-pip...${RESET}"
    if ! $PY_BIN -m ensurepip --upgrade --default-pip >/dev/null 2>&1; then
        echo "${RED}  ✗ pip is missing AND ensurepip failed.${RESET}"
        echo "  Install pip via your system package manager, e.g.:"
        echo "    • Debian/Ubuntu:  sudo apt install python3-pip"
        echo "    • Fedora/RHEL:     sudo dnf install python3-pip"
        echo "    • macOS Homebrew:  brew install python  (Apple-shipped Python disables ensurepip)"
        echo "    • Windows:         python -m ensurepip --upgrade  (from Admin shell)"
        exit 1
    fi
fi
echo "${GREEN}  ✓ pip is ready${RESET}"
echo ""

# ============================================================================
# STEP 4 of 5: Download CleanBoost wheel from GitHub
# ----------------------------------------------------------------------------
# Tries the prebuilt wheel first (5 kB, instant download).
# Falls back to source tarball if the wheel is missing on the mirror.
# ============================================================================
echo "${BOLD}─── STEP 4 of 5: Download CleanBoost v${VERSION} from GitHub ───${RESET}"
echo "  We fetch the official wheel from GitHub and place it in a temp dir."
echo "  No installation happens yet — just download. (5 kB, ~1 second on broadband.)"
echo ""

# Setup tmp dir + cleanup trap (always runs, even on Ctrl+C)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

WHEEL_NAME="cleanboost-${VERSION}-py3-none-any.whl"
WHEEL_URL="${REPO_RAW_URL}/dist/${WHEEL_NAME}"
DL_TARGET="${TMP_DIR}/${WHEEL_NAME}"

if curl -fsSL "$WHEEL_URL" -o "$DL_TARGET" 2>/dev/null; then
    echo "${GREEN}  ✓ Prebuilt wheel downloaded.${RESET}"
else
    echo "${YELLOW}  Wheel not at raw URL — falling back to source tarball (will build locally).${RESET}"
    DL_TARGET="${TMP_DIR}/main.tar.gz"
    if ! curl -fsSL "$ARCHIVE_URL" -o "$DL_TARGET"; then
        echo "${RED}  ✗ Could not download CleanBoost artifacts. Check your internet connection.${RESET}"
        exit 1
    fi
    echo "${GREEN}  ✓ Source tarball downloaded.${RESET}"
fi
echo ""

# ============================================================================
# STEP 5 of 5: pip install + verify
# ----------------------------------------------------------------------------
# --user avoids sudo, installs to ~/.local/bin (or AppData\Roaming\Python on Win).
# Then we run cleanboost --version and STRICTLY check it equals the expected.
# ============================================================================
echo "${BOLD}─── STEP 5 of 5: Install with pip + verify ───${RESET}"
echo "  Running \`pip install --user\` to register 'cleanboost' in your PATH."
echo "  This places the binary in \$(python3 -m site --user-base)/bin/."
echo ""

if ! $PY_BIN -m pip install --user --upgrade "$DL_TARGET"; then
    echo "${RED}  ✗ pip install failed.${RESET}"
    echo "  Common causes:"
    echo "    • No write permission to ~/.local (corporate laptop?). Use venv instead:"
    echo "        python3 -m venv ~/cleanboost-venv"
    echo "        ~/cleanboost-venv/bin/python -m pip install --upgrade \"$DL_TARGET\""
    echo "    • Apple-shipped macOS Python: install Homebrew Python:"
    echo "        brew install python && re-run this installer"
    echo "    • PEP 668 externally-managed environment: re-run with:"
    echo "        python3 -m pip install --user --break-system-packages \"$DL_TARGET\""
    exit 1
fi
echo "${GREEN}  ✓ pip install succeeded.${RESET}"
echo ""

# ----- Verify installation -----
echo "${BOLD}─── Verify ───${RESET}"
USER_BASE=$($PY_BIN -m site --user-base 2>/dev/null || echo "")

if [[ "$OS_RAW" == *MINGW* ]] || [[ "$OS_RAW" == *MSYS* ]] || [[ "$OS_RAW" == *CYGWIN* ]]; then
    BIN_PATH="${USER_BASE}/Scripts/cleanboost"
else
    BIN_PATH="${USER_BASE}/bin/cleanboost"
fi

if command -v cleanboost >/dev/null 2>&1; then
    CB_CMD="cleanboost"
elif [ -n "$USER_BASE" ] && [ -f "$BIN_PATH" ]; then
    CB_CMD="$BIN_PATH"
else
    echo "${YELLOW}  pip install succeeded but \`cleanboost\` is not in PATH.${RESET}"
    echo "  Add this to your shell profile (~/.zshrc, ~/.bashrc, etc.):"
    echo "      export PATH=\"\$(${PY_BIN} -m site --user-base)/bin:\$PATH\""
    echo "  Then: cleanboost --version"
    exit 0
fi

VER_OUTPUT=$("$CB_CMD" --version 2>&1 || true)

# Strict literal match: avoid false positives (e.g. "3.1.20" or "X-3.1.2-Y").
if [ "$VER_OUTPUT" = "cleanboost ${VERSION}" ]; then
    echo "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${RESET}"
    echo "${BOLD}${GREEN}   ✓ Installation complete!   ${VER_OUTPUT}${RESET}"
    echo "${BOLD}${GREEN}════════════════════════════════════════════════════════════════${RESET}"
    echo ""
    if [ "$CB_CMD" = "$BIN_PATH" ] && ! command -v cleanboost >/dev/null 2>&1; then
        echo "${YELLOW}Note: \`cleanboost\` is not yet on your PATH. Run via full path:${RESET}"
        echo "  $BIN_PATH"
        echo "${YELLOW}Or add to PATH (one-time):${RESET}"
        echo "  export PATH=\"$USER_BASE/bin:\$PATH\""
    fi
    echo ""
    echo "Try it now:"
    echo "  ${BOLD}cleanboost --version${RESET}"
    echo "  ${BOLD}cleanboost --quick${RESET}      # runs OPTIMIZE + CLEAN silently"
    echo "  ${BOLD}cleanboost${RESET}              # interactive 3-button menu"
    exit 0
else
    echo "${RED}  ✗ Version verification failed.${RESET}"
    echo "  Expected: cleanboost ${VERSION}"
    echo "  Got:      ${VER_OUTPUT}"
    exit 1
fi
