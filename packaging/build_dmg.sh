#!/usr/bin/env bash

# =====================================================
# Pre-flight checks (require Python 3.10+ and PyInstaller 6+ for universal2)
# =====================================================
PY_VER=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]); then
  echo "[ERROR] Python 3.10+ required for universal2 builds (got $PY_VER)"
  exit 1
fi

# Universal2 builds require macOS SDK 11+ (Big Sur o newer). Host older
# produce 'arm64-only' o 'x86_64-only' silenciosamente.
# macOS 11+ (Big Sur) required for universal2 builds. Override via env var
# `MACOS_FORCE_BUILD=1` if you intend a thin (Intel-only or arm64-only) build
# anyway — sets major to 99 in the check and skips the gate.
if [ "$(uname)" = "Darwin" ]; then
  if [ "$MACOS_FORCE_BUILD" = "1" ]; then
    echo "[WARN] MACOS_FORCE_BUILD=1 set; bypassing macOS 11+ guard (result will be thin binary)"
  else
    HOST_MAC_MAJOR=$(sw_vers -productVersion | cut -d. -f1)
    if [ "$HOST_MAC_MAJOR" -lt 11 ] 2>/dev/null; then
      echo "[ERROR] macOS 11+ (Big Sur) requerida para builds universal2. HOST macOS=$HOST_MAC_MAJOR"
      echo "        Para build 'thin' intencional (x86_64-only o arm64-only), export MACOS_FORCE_BUILD=1 y reintenta."
      exit 1
    fi
  fi
fi

if ! python3 -c 'import PyInstaller; assert PyInstaller.__version__ >= "6.0"' 2>/dev/null; then
  echo "[ERROR] PyInstaller 6.0+ required (universal2 support). pip install 'pyinstaller>=6.0'"
  exit 1
fi

#
# packaging/build_dmg.sh
# ======================
# Compila CLEANBOOST.app vía PyInstaller y lo empaqueta como DMG de macOS.
# Target: MacBook Pro 2017 13" TouchBar (Intel x86_64, macOS 13+).
#
# Uso (desde la raíz del proyecto):
#     chmod +x packaging/build_dmg.sh
#     ./packaging/build_dmg.sh
#
# Output (todo dentro de packaging/build/ para no contaminar el repo):
#     - dist/CLEANBOOST.app            (bundle .app con firma ad-hoc)
#     - CLEANBOOST_v3.0_x86_64.dmg     (instalador drag-to-Applications)
#
set -euo pipefail

# ───────── Config ─────────
APP_NAME="CLEANBOOST"
VERSION="3.1.1"
TARGET_ARCH="universal2"  # macOS universal2: Intel x86_64 + Apple Silicon arm64
BUNDLE_ID="com.cyberpunk.cleanboost"
DMG_NAME="${APP_NAME}_v${VERSION}_${TARGET_ARCH}.dmg"
PY_VER="3.11"

BUILD_DIR="packaging/build"
VENV_DIR="${BUILD_DIR}/venv"
RESIZE_DIR="${BUILD_DIR}/_resize"
ICONSET_DIR="${BUILD_DIR}/icon.iconset"
APP_PATH="${BUILD_DIR}/dist/${APP_NAME}.app"
DMG_OUTPUT="${BUILD_DIR}/${DMG_NAME}"

# ───────── Setup: ir a raíz del proyecto ─────────
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "${SCRIPT_DIR}/.." && pwd )"
cd "$PROJECT_ROOT"
echo "▶ Project root: ${PROJECT_ROOT}"

# ───────── Step 1/6 — Homebrew + Python 3.12 ─────────
echo ""
echo "▶ Step 1/6   Homebrew + Python ${PY_VER}"

if ! command -v brew >/dev/null 2>&1; then
  echo "  ✗ Homebrew no está instalado. Instálalo desde https://brew.sh/ primero."
  exit 1
fi

BREW_PREFIX="$(brew --prefix)"
PY_BIN="${BREW_PREFIX}/bin/python${PY_VER}"
if [ ! -x "$PY_BIN" ]; then
  echo "  · python@${PY_VER} no encontrado. Instalando con brew..."
  echo "    (si no hay bottle Intel, compilará de fuente: 5-10 min)"
  brew install "python@${PY_VER}"
fi

"$PY_BIN" - <<'PY'
import sys, tkinter
print(f"  · python: {sys.version.split()[0]}, tk: {tkinter.TkVersion}")
PY

# ───────── Step 2/6 — venv + dependencias ─────────
echo ""
echo "▶ Step 2/6   venv + pyinstaller + pillow"

mkdir -p "$BUILD_DIR"
if [ ! -d "$VENV_DIR" ]; then
  "$PY_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --quiet --upgrade pip pyinstaller pillow

# ───────── Step 3/6 — Icon (1024 → .icns) ─────────
echo ""
echo "▶ Step 3/6   Generar ícono (1024 → .icns)"

rm -rf "$ICONSET_DIR" "$RESIZE_DIR"
mkdir -p "$ICONSET_DIR" "$RESIZE_DIR"

python packaging/make_icon.py "${BUILD_DIR}/icon_base.png"

# Generar cada tamaño único vía sips y luego copiar a los nombres del spec .iconset
for sz in 16 32 64 128 256 512 1024; do
  sips -z "$sz" "$sz" "${BUILD_DIR}/icon_base.png" \
       --out "${RESIZE_DIR}/icon_${sz}.png" >/dev/null
done

cp "${RESIZE_DIR}/icon_16.png"   "$ICONSET_DIR/icon_16x16.png"
cp "${RESIZE_DIR}/icon_32.png"   "$ICONSET_DIR/icon_16x16@2x.png"
cp "${RESIZE_DIR}/icon_32.png"   "$ICONSET_DIR/icon_32x32.png"
cp "${RESIZE_DIR}/icon_64.png"   "$ICONSET_DIR/icon_32x32@2x.png"
cp "${RESIZE_DIR}/icon_128.png"  "$ICONSET_DIR/icon_128x128.png"
cp "${RESIZE_DIR}/icon_256.png"  "$ICONSET_DIR/icon_128x128@2x.png"
cp "${RESIZE_DIR}/icon_256.png"  "$ICONSET_DIR/icon_256x256.png"
cp "${RESIZE_DIR}/icon_512.png"  "$ICONSET_DIR/icon_256x256@2x.png"
cp "${RESIZE_DIR}/icon_512.png"  "$ICONSET_DIR/icon_512x512.png"
cp "${RESIZE_DIR}/icon_1024.png" "$ICONSET_DIR/icon_512x512@2x.png"
rm -rf "$RESIZE_DIR"

iconutil -c icns "$ICONSET_DIR" -o "${BUILD_DIR}/icon.icns"
echo "  ✓ ${BUILD_DIR}/icon.icns"

# ───────── Step 4/6 — PyInstaller ─────────
echo ""
echo "▶ Step 4/6   PyInstaller (${TARGET_ARCH}, --windowed --onedir)"

mkdir -p "${BUILD_DIR}/pywork"
rm -rf "${BUILD_DIR}/build" "${BUILD_DIR}/dist"

pyinstaller --noconfirm \
  --windowed \
  --onedir \
  --target-arch "${TARGET_ARCH}" \
  --distpath "${BUILD_DIR}/dist" \
  --workpath "${BUILD_DIR}/pywork/work" \
  --specpath "${BUILD_DIR}/pywork" \
  --icon "${BUILD_DIR}/icon.icns" \
  --name "${APP_NAME}" \
  --osx-bundle-identifier "${BUNDLE_ID}" \
  --collect-all tkinter \
  --collect-submodules tkinter \
  --hidden-import=tkinter \
  main.py

# ───────── Step 5/6 — Info.plist + ad-hoc sign ─────────
echo ""
echo "▶ Step 5/6   Info.plist (Retina + categoría) + firma ad-hoc"

PLIST="${APP_PATH}/Contents/Info.plist"

# PlistBuddy: Add falla si la clave existe, Set falla si falta. Probamos ambos.
plist_set() {
  local key="$1" type="$2" value="$3"
  /usr/libexec/PlistBuddy -c "Add :${key} ${type} ${value}" "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Set :${key} ${value}" "$PLIST"
}

plist_set "NSHighResolutionCapable"      "bool"   "true"
plist_set "CFBundleShortVersionString"   "string" "$VERSION"
plist_set "CFBundleVersion"              "string" "3"
plist_set "LSApplicationCategoryType"    "string" "public.app-category.utilities"

# Limpia atributos extendidos que a veces rompen codesign (incluido quarantine)
xattr -cr "$APP_PATH" || true

# Firma ad-hoc robusta para Gatekeeper en macOS 13:
# 1) Pre-firmar cada .dylib / .so individualmente (--deep no siempre propaga).
# 2) Firma final del bundle con --force --deep --sign -.
# Sin --options runtime porque requeriría entitlements (no estamos notarizando).
echo "  · pre-firmando librerías dinámicas (.dylib / .so)…"
find "$APP_PATH" \( -name "*.dylib" -o -name "*.so" \) \
  -exec codesign --force --sign - {} \; 2>/dev/null || true
codesign --force --deep --sign - "$APP_PATH"
echo "  ✓ firma ad-hoc aplicada"

# Verificación completa (no aborta el build; log a archivo para auditoría)
VERIFY_LOG="${BUILD_DIR}/codesign_verify.log"
if codesign --verify --verbose=2 "$APP_PATH" >"$VERIFY_LOG" 2>&1; then
  echo "  ✓ codesign --verify OK (log: $VERIFY_LOG)"
else
  echo "  ⚠ codesign --verify reportó advertencias (ver $VERIFY_LOG)"
fi

# Sanity check de arquitectura del binario principal (MBP 2017 = Intel)
BIN="$APP_PATH/Contents/MacOS/${APP_NAME}"
if [ -x "$BIN" ] && command -v lipo >/dev/null 2>&1; then
  echo "  · lipo: $(lipo -info "$BIN" 2>&1 | head -1)"
  case "$(lipo -info "$BIN" 2>&1)" in
    *x86_64*) echo "  ✓ binario Intel x86_64 (compatible MBP 2017)";;
    *arm64*)  echo "  ⚠ binario ARM64 detectado (MBP 2017 NO lo podrá ejecutar)";;
    *)        echo "  ⚠ arquitectura no reconocida; revisar manualmente";;
  esac
fi

# ───────── Step 6/6 — DMG ─────────
echo ""
echo "▶ Step 6/6   Empaquetar DMG (hdiutil UDZO, drag-to-Applications)"

rm -rf "${BUILD_DIR}/staging" "$DMG_OUTPUT"
mkdir -p "${BUILD_DIR}/staging"
cp -a "$APP_PATH" "${BUILD_DIR}/staging/"
ln -s /Applications "${BUILD_DIR}/staging/Applications"

hdiutil create \
  -volname "${APP_NAME}" \
  -srcfolder "${BUILD_DIR}/staging" \
  -ov \
  -format UDZO \
  "$DMG_OUTPUT"

DMG_MB="$(du -m "$DMG_OUTPUT" | awk '{print $1}')"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo " ✅ BUILD COMPLETO"
echo "═══════════════════════════════════════════════════════════════"
echo "  App:   ${APP_PATH}"
echo "  DMG:   ${DMG_OUTPUT}  (${DMG_MB} MB)"
echo ""
echo "  Para probarlo en tu MacBook Pro 2017:"
echo "  1) open \"${DMG_OUTPUT}\""
echo "  2) Arrastra CLEANBOOST.app a /Applications"
echo "  3) Primera vez: clic derecho en el .app → 'Abrir' (Gatekeeper bypass)"
echo "  4) Las siguientes ya lo abres normal desde Launchpad."
echo ""
echo "  Re-runs son rápidos (~30 s) — el venv y bottle de Python se reutilizan."
echo "═══════════════════════════════════════════════════════════════"
