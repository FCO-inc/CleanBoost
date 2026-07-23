#!/usr/bin/env python3
"""
packaging/make_icon.py
======================
Genera proceduralmente el ícono de CLEANBOOST a 1024×1024 px.

El build script luego lo convierte a `.icns` con las herramientas nativas de
macOS (`sips` + `iconutil`). Refleja el lenguaje visual de la app:

  - Fondo #0A0A0A   (BG)
  - Verde neón #00FF41 (ACCENT) en esquinas HUD y textos principales
  - Verde oscuro #00B82E (ACCENT_LO) en subtítulos y barras
  - Esquina HUD brackets que espejan `_draw_corners()` de main.py

Uso:
    python packaging/make_icon.py [ruta_de_salida.png]
    (Por defecto: packaging/build/icon_base.png)
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ─── Paleta sincronizada con main.py ───────────────────────────────
BG         = (10,   10,  10, 255)   # #0A0A0A fondo
# Tema v3.1.1 unificado en 4 colores (matches ANSI 256-color en main.py):
#   ACCENT     = steel_blue  #5F87FF  ANSI 38;5;75   warnings
#   ACCENT_HI  = bright_white #F5F5F5 ANSI 38;5;231  headers/banner
#   ACCENT_OK  = bright_green #5FFF87 ANSI 38;5;46  OK mark / progress bar
#   ACCENT_LO  = bright_green dim #2FA85F ANSI cercano a 22 shadows
ACCENT     = ( 95, 135, 255, 255)   # #5F87FF  steel_blue (warning)
ACCENT_HI  = (245, 245, 245, 255)   # #F5F5F5  bright_white (headers)
ACCENT_OK  = ( 95, 255, 135, 255)   # #5FFF87  bright_green (OK)
ACCENT_LO  = ( 47, 168,  95, 255)   # #2FA85F  green dim (deprecated alias retrocompatible)

SIZE = 1024  # canvas size — macOS source for iconutil


# ─── Búsqueda de fuente con fallback robusto ────────────────────────
def _font(px: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Devuelve la mejor fuente macOS disponible. Si ninguna carga,
    cae al bitmap default (legibilidad mínima pero no rompe)."""
    candidates: list[tuple[str, int]] = [
        # path, font_index (some .ttc contain Regular=0 Bold=1)
        ("/System/Library/Fonts/Menlo.ttc",                      1 if bold else 0),
        ("/System/Library/Fonts/Supplemental/Arial Black.ttf",   0),
        ("/Library/Fonts/Arial Bold.ttf",                         0),
        ("/System/Library/Fonts/Supplemental/Impact.ttf",        0),
        ("/System/Library/Fonts/Helvetica.ttc",                  1 if bold else 0),
    ]
    last_error: Exception | None = None
    for path, idx in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, px, index=idx)
            except (OSError, IndexError) as exc:
                last_error = exc
                continue
    # Try to load any default font as last-resort
    try:
        return ImageFont.load_default(size=px)
    except (AttributeError, TypeError):
        return ImageFont.load_default()
    finally:
        # Silence unused warning while keeping the diagnostic accessible
        _ = last_error


# ─── Brackets HUD que espejan `_draw_corners()` de la app ─────────
def _hud_brackets(draw: ImageDraw.ImageDraw,
                  margin: int = 64,
                  length: int = 200,
                  thick: int = 24) -> None:
    """Cuatro esquinas tipo '[' en verde neón."""
    s = SIZE
    corners = [
        # top-left  └
        [(margin,         margin + length), (margin,         margin),         (margin + length, margin)],
        # top-right ┘
        [(s - margin - length, margin),      (s - margin,        margin),         (s - margin,     margin + length)],
        # bottom-left ┌
        [(margin,         s - margin - length), (margin,       s - margin),      (margin + length, s - margin)],
        # bottom-right ┐
        [(s - margin - length, s - margin),  (s - margin,        s - margin),      (s - margin,     s - margin - length)],
    ]
    for pts in corners:
        draw.line([pts[0], pts[1]], fill=ACCENT, width=thick)
        draw.line([pts[1], pts[2]], fill=ACCENT, width=thick)


# ─── Barra de progreso decorativa ──────────────────────────────────
def _progress_bar(draw: ImageDraw.ImageDraw) -> None:
    w, h = 600, 30
    x1 = (SIZE - w) // 2
    y1 = 820
    x2 = x1 + w
    y2 = y1 + h
    draw.rectangle([x1, y1, x2, y2], outline=ACCENT_LO, width=4)
    fill_x = x1 + 4 + int((w - 8) * 0.7)
    draw.rectangle([x1 + 4, y1 + 4, fill_x, y2 - 4], fill=ACCENT)


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1
               else "packaging/build/icon_base.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(img)

    _hud_brackets(draw)

    # ── Marca principal: "CB" en bloque (legible incluso a 16×16) ──
    cb_font = _font(380, bold=True)
    draw.text((SIZE // 2, 430), "CB", fill=ACCENT, font=cb_font, anchor="mm")

    # ── Nombre + subtítulo ──
    title_font = _font(85, bold=True)
    draw.text((SIZE // 2, 690), "CLEANBOOST", fill=ACCENT, font=title_font, anchor="mm")

    sub_font = _font(38, bold=False)
    draw.text((SIZE // 2, 760), "> SYSTEM OPTIMIZER v3.0",
              fill=ACCENT_LO, font=sub_font, anchor="mm")

    _progress_bar(draw)

    img.save(out, "PNG", optimize=True)
    print(f"  ✓ icon base:  {out}  ({SIZE}×{SIZE} PNG)")


if __name__ == "__main__":
    main()
