#!/usr/bin/env bash
# ==============================================================================
# CleanBoost v3.1.2 Installer (curl | bash single-command)
# ==============================================================================
# Friendly default — shows clean status lines + final "Done!".
# For full debug output, run with --verbose:
#   curl -sSL https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/install.sh | bash -s -- --verbose
# ==============================================================================

set -euo pipefail
export LC_ALL=C

# ---- Flag parsing ----
VERBOSE=0
for arg in "$@"; do
    case "$arg" in
        --verbose|-v) VERBOSE=1 ;;
        --quiet|-q|--silent) VERBOSE=0 ;;
        --help|-h)
            echo "Usage: curl -sSL .../install.sh | bash [-s -- [--verbose]]"
            exit 0
            ;;
    esac
done

# ---- Colors (only on TTY) ----
if [ -t 1 ] && command -v tput >/dev/null 2>&1 && [ -n "${TERM:-}" ] && [ "${TERM:-}" != "dumb" ]; then
    RED=$(tput setaf 1)
    GREEN=$(tput setaf 2)
    YELLOW=$(tput setaf 3)
    BOLD=$(tput bold)
    RESET=$(tput sgr0)
else
    RED="" GREEN="" YELLOW="" BOLD="" RESET=""
fi

# ---- Output helpers ----
ok()    { echo "${GREEN}✓ $@${RESET}"; }                       # always, green check
warn()  { echo "${YELLOW}⚠ $@${RESET}"; }                      # always, yellow warning
err()   { echo "${RED}✗ $@${RESET}" >&2; exit 1; }            # always, red + abort
say()   { [ "$VERBOSE" = "1" ] && echo "$@" || true; }        # only in --verbose mode

# ---- Welcome banner (always shown, friendly) ----
echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                                                            ║"
echo "║             C L E A N B O O S T    I N S T A L L E R       ║"
echo "║                                                            ║"
echo "║   Fast, simple, 100% free terminal software.              ║"
echo "║   Detects games. Optimizes caches. 100% local.            ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# ============================================================================
# STEP 1 — Detect your operating system
# ============================================================================
OS_RAW="$(uname -s 2>/dev/null || echo unknown)"
say "Detecting OS..."
case "$OS_RAW" in
    Darwin)
        OS="macos"
        ok "Detected macOS"
        ;;
    MINGW*|CYGWIN*|MSYS*|Windows_NT)
        OS="windows"
        ok "Detected Windows"
        ;;
    Linux)
        echo "${BOLD}CleanBoost does not run on Linux.${RESET} (Linux manages caches natively.)"
        exit 0
        ;;
    *)
        err "Unsupported OS: $OS_RAW. CleanBoost runs on macOS and Windows."
        ;;
esac

# ============================================================================
# STEP 2 — Verify Python 3.8+ (or auto-bootstrap)
# ============================================================================
say "Looking for Python 3.8+..."

# ============================================================================
# On macOS without Command Line Tools installed, /usr/bin/python3 is a tiny
# Apple-supplied stub (a handful of bytes of shell-script text) that TRIGGERS
# the macOS "python3 requires installing the developer tools" popup the
# moment we invoke it. Detect that stub here by file size and skip STRAIGHT
# to the portable-Python bootstrap path, so non-technical users never see
# the developer-tools dialog.
# ============================================================================
is_real_python_bin() {
    local binpath
    binpath=$(command -v "$1" 2>/dev/null) || return 1
    [ -x "$binpath" ] || return 1
    if [[ "$OS_RAW" == "Darwin" ]]; then
        # Real CPython on macOS: ~2-7 MB Mach-O binary.
        # Apple CLT stub: < 1 KB text/shell script.
        local size
        size=$(wc -c < "$binpath" 2>/dev/null || echo 0)
        # Threshold 100 KB: comfortably below any real Python, far above any stub.
        [ "$size" -gt 100000 ] || return 1
    fi
    return 0
}

PY_BIN=""
if command -v python3 >/dev/null 2>&1 && is_real_python_bin python3; then
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
        PY_BIN="python3"
    fi
fi
if [ -z "$PY_BIN" ] && command -v python >/dev/null 2>&1 && is_real_python_bin python; then
    if python -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" 2>/dev/null; then
        PY_BIN="python"
    fi
fi

if [ -z "$PY_BIN" ]; then
    say "  Python 3.8+ not found. Bootstrapping portable Python 3.11 from python-build-standalone (~15 MB)..."
    PBS_DIR="$HOME/.cache/cleanboost/python"
    PBS_DATE="20240415"
    case "$OS_RAW" in
        Darwin)
            case "$(uname -m)" in
                arm64|aarch64) PBS_FILE="cpython-3.11.9+${PBS_DATE}-aarch64-apple-darwin-install_only.tar.gz" ;;
                x86_64)        PBS_FILE="cpython-3.11.9+${PBS_DATE}-x86_64-apple-darwin-install_only.tar.gz" ;;
                *) err "Unsupported macOS architecture: $(uname -m)" ;;
            esac
            PY_BIN="$PBS_DIR/bin/python3"
            ;;
        MINGW*|CYGWIN*|MSYS*|Windows_NT)
            PBS_FILE="cpython-3.11.9+${PBS_DATE}-x86_64-pc-windows-msvc-install_only.tar.gz"
            PY_BIN="$PBS_DIR/python.exe"
            ;;
    esac
    PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_DATE}/${PBS_FILE}"
    if [ ! -x "$PY_BIN" ]; then
        mkdir -p "$PBS_DIR"
        say "  → Downloading $PBS_URL"
        if ! curl -fsSL -o "$PBS_DIR/python.tar.gz" "$PBS_URL"; then
            err "Could not download Python. Please install Python 3.8+ from https://www.python.org/downloads/ and re-run."
        fi
        say "  → Extracting..."
        if ! tar -xzf "$PBS_DIR/python.tar.gz" -C "$PBS_DIR" --strip-components=1 2>/dev/null; then
            err "Could not extract the portable Python archive. Installation aborted."
        fi
        rm -f "$PBS_DIR/python.tar.gz"
    fi
fi

PY_VERSION="$($PY_BIN --version 2>&1 | head -1)"
ok "Found Python $PY_VERSION"

# ============================================================================
# STEP 3 — Verify pip is available
# ============================================================================
say "Verifying pip..."
if ! $PY_BIN -m pip --version >/dev/null 2>&1; then
    say "  pip not detected. Attempting ensurepip..."
    if ! $PY_BIN -m ensurepip --upgrade --default-pip >/dev/null 2>&1; then
        err "pip could not be installed. Please install Python 3.8+ with pip and re-run."
    fi
fi
ok "pip is ready"

# ============================================================================
# STEP 4 — Download CleanBoost
# ============================================================================
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

VERSION="3.1.2"
WHEEL_NAME="cleanboost-${VERSION}-py3-none-any.whl"
WHEEL_URL="https://raw.githubusercontent.com/FCO-inc/CleanBoost/main/dist/${WHEEL_NAME}"
DL_TARGET="${TMP_DIR}/${WHEEL_NAME}"

say "Downloading CleanBoost $VERSION from GitHub..."
if ! curl -fsSL "$WHEEL_URL" -o "$DL_TARGET" 2>/dev/null; then
    say "  Prebuilt wheel missing. Falling back to source tarball..."
    DL_TARGET="${TMP_DIR}/main.tar.gz"
    if ! curl -fsSL "https://github.com/FCO-inc/CleanBoost/archive/refs/heads/main.tar.gz" -o "$DL_TARGET"; then
        err "Could not download CleanBoost. Check your internet connection."
    fi
fi
ok "Downloaded CleanBoost"

# ============================================================================
# STEP 5 — Install with pip (with PEP 668 silent retry) + verify
# ============================================================================
say "Installing (this takes ~5 seconds)..."

# Try first without --break-system-packages (clean default for non-PEP-668 systems).
if ! $PY_BIN -m pip install --user --upgrade "$DL_TARGET" >/dev/null 2>&1; then
    say "  pip install failed. Retrying with --break-system-packages (PEP 668 compliance)..."
    if ! $PY_BIN -m pip install --user --break-system-packages --upgrade "$DL_TARGET" >/dev/null 2>&1; then
        err "Could not install. Please install Python 3.8+ with pip and re-run, or visit https://github.com/FCO-inc/CleanBoost/issues"
    fi
fi
ok "Installed CleanBoost"

# Locate installed binary
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
    warn "Install succeeded but 'cleanboost' is not yet on your PATH."
    say "  Add this to your shell profile (~/.zshrc or ~/.bashrc):"
    # NOTE: use USER_BASE (already evaluated earlier via $PY_BIN), NOT a raw
    # `$(python3 -m site --user-base)` shell substitution. That would re-invoke
    # raw python3 on macOS without Command Line Tools and re-trigger the
    # developer-tools popup we already neutralized in STEP 2.
    if [ -n "$USER_BASE" ]; then
        say "      export PATH=\"${USER_BASE}/bin:\$PATH\""
    else
        say "      export PATH=\"\$HOME/.local/bin:\$PATH\""
    fi
    say "  Then open a new Terminal window and run: cleanboost --version"
    exit 0
fi

say "Verifying..."
VER_OUTPUT=$("$CB_CMD" --version 2>&1 || true)
if [ "$VER_OUTPUT" != "cleanboost ${VERSION}" ]; then
    err "Version verification failed. Got: '$VER_OUTPUT' — expected: 'cleanboost ${VERSION}'."
fi

# ---- Final success banner ----
echo ""
echo "${GREEN}╔════════════════════════════════════════════════════════════╗${RESET}"
echo "${GREEN}║                                                            ║${RESET}"
echo "${GREEN}║   ✓ Done! cleanboost ${VERSION} is installed.              ║${RESET}"
echo "${GREEN}║                                                            ║${RESET}"
echo "${GREEN}╚════════════════════════════════════════════════════════════╝${RESET}"
echo ""
# Show run instructions only if cleanboost is already on PATH
if command -v cleanboost >/dev/null 2>&1; then
    echo "Try it now:"
    echo ""
    echo "    ${BOLD}cleanboost --version${RESET}    (check it works)"
    echo "    ${BOLD}cleanboost --quick${RESET}       (auto-detect + clean in one shot)"
    echo "    ${BOLD}cleanboost${RESET}               (interactive 3-button menu)"
    echo ""
fi

# If cleanboost is not on PATH, auto-append the bin directory to the shell
# config file so the next Terminal session finds it without manual steps.
if ! command -v cleanboost >/dev/null 2>&1; then
    PATH_DIR="${USER_BASE}/bin"
    SHELL_RC=""
    [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
    [ -f "$HOME/.bash_profile" ] && SHELL_RC="$HOME/.bash_profile"
    [ -f "$HOME/.bashrc" ] && SHELL_RC="$HOME/.bashrc"

    if [ -n "$SHELL_RC" ] && ! grep -qF "$PATH_DIR" "$SHELL_RC" 2>/dev/null; then
        echo "" >> "$SHELL_RC"
        echo "# Added by CleanBoost v${VERSION} installer" >> "$SHELL_RC"
        echo "export PATH=\"${PATH_DIR}:\$PATH\"" >> "$SHELL_RC"
        ok "Added ${BOLD}${PATH_DIR}${RESET} to your PATH"
    fi

    echo ""
    echo "  Open a ${BOLD}NEW Terminal window${RESET} and run:"
    echo "    ${BOLD}cleanboost${RESET}"
    echo ""
fi
