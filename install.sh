#!/usr/bin/env bash
# ==============================================================================
# CleanBoost Installer (curl | bash single-command)
# ==============================================================================
# BUMP THIS VERSION WHEN PUBLISHING A NEW RELEASE.
# Usage from any machine with curl + bash:
#   curl -sSL https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.sh | bash
# ==============================================================================
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

echo "${BOLD}${BLUE}═══ CleanBoost v${VERSION} Installer ═══${RESET}"

# 1. OS Detection (informational; pip handles cross-platform details)
OS="$(uname -s)"
echo "${GREEN}> Detected OS: ${OS}${RESET}"

# 2. Python 3 detection + version check
if command -v python3 >/dev/null 2>&1; then
    PY_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PY_BIN="python"
else
    echo "${RED}Error: Python is not installed. Please install Python 3.8+ from python.org.${RESET}"
    exit 1
fi

PY_VER=$($PY_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if $PY_BIN -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo "${GREEN}> Detected Python ${PY_VER}${RESET}"
else
    echo "${RED}Error: CleanBoost requires Python 3.8 or newer. You have ${PY_VER}.${RESET}"
    echo "Check: $PY_BIN --version"
    exit 1
fi

# 3. Pip detection (with ensurepip fallback)
if ! $PY_BIN -m pip --version >/dev/null 2>&1; then
    echo "${YELLOW}> pip not detected. Attempting ensurepip --default-pip...${RESET}"
    if ! $PY_BIN -m ensurepip --upgrade --default-pip >/dev/null 2>&1; then
        echo "${RED}Error: pip is missing and ensurepip failed.${RESET}"
        echo "Install pip via system package manager (e.g. sudo apt install python3-pip) then rerun."
        exit 1
    fi
fi
echo "${GREEN}> pip ready${RESET}"

# 4. Setup tmp dir + cleanup trap (always runs, even on Ctrl+C)
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

# 5. Download artifact (wheel first, fallback to repo tarball)
WHEEL_NAME="cleanboost-${VERSION}-py3-none-any.whl"
WHEEL_URL="${REPO_RAW_URL}/dist/${WHEEL_NAME}"

echo "${BLUE}> Downloading CleanBoost v${VERSION}...${RESET}"
DL_TARGET="${TMP_DIR}/${WHEEL_NAME}"
if ! curl -fsSL "$WHEEL_URL" -o "$DL_TARGET" 2>/dev/null; then
    echo "${YELLOW}> Wheel not at raw URL. Falling back to repo source tarball...${RESET}"
    DL_TARGET="${TMP_DIR}/main.tar.gz"
    if ! curl -fsSL "$ARCHIVE_URL" -o "$DL_TARGET"; then
        echo "${RED}Error: Could not download CleanBoost artifacts. Check your internet connection.${RESET}"
        exit 1
    fi
    echo "${GREEN}> Source tarball downloaded.${RESET}"
else
    echo "${GREEN}> Wheel downloaded.${RESET}"
fi

# 6. Install via pip (idempotent, --user avoids sudo)
echo "${BLUE}> Installing via pip --user...${RESET}"
if ! $PY_BIN -m pip install --user --upgrade "$DL_TARGET"; then
    echo "${RED}Error: pip install failed.${RESET}"
    echo "Common causes:"
    echo "  - No write permission to ~/.local (corporate laptop?) → use venv instead:"
    echo "      python3 -m venv ~/cleanboost-venv && ~/cleanboost-venv/bin/python -m pip install --upgrade dist/cleanboost-${VERSION}-py3-none-any.whl"
    echo "  - On macOS Apple-shipped Python: install Homebrew Python:"
    echo "      brew install python && re-run this installer"
    echo "  - On externally-managed environment (PEP 668), add --break-system-packages flag"
    exit 1
fi

# 7. Verification
echo "${BLUE}> Verifying cleanboost --version...${RESET}"
USER_BASE=$($PY_BIN -m site --user-base 2>/dev/null || echo "")
if [[ "$OS" == *"MINGW"* ]] || [[ "$OS" == *"MSYS"* ]] || [[ "$OS" == *"CYGWIN"* ]]; then
    BIN_PATH="${USER_BASE}/Scripts/cleanboost"
else
    BIN_PATH="${USER_BASE}/bin/cleanboost"
fi

if command -v cleanboost >/dev/null 2>&1; then
    CB_CMD="cleanboost"
elif [ -n "$USER_BASE" ] && [ -f "$BIN_PATH" ]; then
    CB_CMD="$BIN_PATH"
else
    echo "${YELLOW}Pip install succeeded but \`cleanboost\` is not in PATH.${RESET}"
    echo "PATH workaround: add this to your shell profile:"
    echo "  export PATH=\"\$(python3 -m site --user-base)/bin:\$PATH\""
    echo "Then run: cleanboost --version"
    exit 0
fi

VER_OUTPUT=$("$CB_CMD" --version 2>&1 || true)
# Strict literal match: avoids false positives like "3.1.20" or "X-3.1.2-Y".
# The exact format from main.py's --version is "cleanboost X.Y.Z".
if [ "$VER_OUTPUT" = "cleanboost ${VERSION}" ]; then
    echo "${BOLD}${GREEN}✓ Installation complete!${RESET}"
    echo "${GREEN}  ${VER_OUTPUT}${RESET}"
    if [ "$CB_CMD" = "$BIN_PATH" ] && ! command -v cleanboost >/dev/null 2>&1; then
        echo "${YELLOW}Note: \`cleanboost\` is not yet on your PATH. Run via full path:${RESET}"
        echo "  $BIN_PATH"
        echo "${YELLOW}Or add to PATH (one-time):${RESET}"
        echo "  export PATH=\"$USER_BASE/bin:\$PATH\""
    fi
    echo ""
    echo "Try it:"
    echo "  ${BOLD}cleanboost --version${RESET}"
    echo "  ${BOLD}cleanboost --quick${RESET}   # runs OPTIMIZE+CLEAN silently"
    echo "  ${BOLD}cleanboost${RESET}           # interactive 3-button menu"
    exit 0
else
    echo "${RED}Error: Version verification failed. Output: ${VER_OUTPUT}${RESET}"
    exit 1
fi
