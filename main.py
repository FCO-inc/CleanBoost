#!/usr/bin/env python3
"""
CLEANBOOST v3 ─ Fast & Simple Terminal Optimizer
======================================================================
CleanBoost is software that runs in the terminal: fast, simple, 100% free.
It detects system specs and installed games (Steam, Epic, Battle.net, GOG,
Minecraft, Roblox), and cleans caches that slow down your PC.

Runs on:
  · macOS, Windows.
  · Detects CPU, RAM, GPU, disk specs.
  · Detects installed games and lets you optimize their caches.
  · Cleans recycle bin, temp files, system cache.
  · Clears shader caches (DirectX, NVIDIA, AMD on Windows; Steam shadercache
    on macOS) for faster game loads.
  · Shows execution time in MM:SS format.
  · Optional daemon mode with weekly reminder (cleanboost --enable-daemon).

Requirements:
    Python 3.8+.
    Zero external dependencies (only the Python standard library).
Usage:
    python main.py                       # Interactive 3-button menu
    python main.py --enable-daemon       # Enable weekly reminders
    python main.py --disable-daemon      # Disable the daemon
    cleanboost --quick                   # Equivalent after pip install
Compatibility: Windows and macOS.

A note on Linux
---------------
Linux is not officially supported: most distributions manage caches,
temp files and the recycle bin natively, making this kind of utility
unnecessary. If you run ``python main.py`` on Linux, the app prints an
informational message and exits with code 0.

Ethical line
------------
CleanBoost optimizes legitimate caches of installed games. It does NOT
distribute support for pirated launchers (warez). This is not a deferred
feature: it is an explicit renunciation.
"""

from __future__ import annotations

import argparse
import locale as _locale
import os
import sys
import shutil
import threading
import subprocess
import platform
import time
from pathlib import Path
from typing import Optional

# Importado a nivel de módulo (no lazy) para que tests con
# ``patch.object(main_mod, "daemon")`` puedan interceptarlo.
import daemon

# Versión expuesta para `cleanboost --version`.
__version__ = "3.1.2"


# ============================================================================
# I18N — strings traducibles (EN/ES).
# La arquitectura es minimalista: un dict inline, una función ``t()`` que
# resuelve la cadena actual y ``get_locale()`` que decide el idioma con
# este orden de precedencia:
#   1. Flag CLI ``--lang=en|es`` (override explícito, gana siempre).
#   2. Variables de entorno en orden: LC_ALL > LC_MESSAGES > LANG.
#   3. ``locale.getlocale()`` de stdlib (lo que el sistema reporta).
#   4. Default ``"en"``.
# El banner ASCII art (CLEANBOOST dibujado) no se traduce porque es brand. El
# subtítulo del banner queda en EN por la misma razón: identidad visual fija.
# ============================================================================
_STRINGS: dict = {
    "en": {
        "header_specs":     "═══ YOUR SPECIFICATIONS ═══",
        "header_games":     "═══ DETECTED GAMES ═══",
        "header_menu":      "═══ WHAT ARE WE DOING TODAY? ═══",
        "header_summary":   "═══ SUMMARY ═══",
        "opt_1_title":      "OPTIMIZE",
        "opt_1_desc":       "shader caches + game\n        libraries",
        "opt_2_title":      "CLEAN",
        "opt_2_desc":       "recycle bin + temp files + system\n        cache",
        "opt_3_title":      "BOTH",
        "opt_3_desc":       "full pass: shaders + system +\n        all platforms",
        "menu_aux":         "Auxiliary: [v] view specs  [q] quit",
        "prompt_choice":    "Choose an option [1-3 / v / q]: ",
        "prompt_invalid":   "⚠  Invalid option.",
        "prompt_proceed":   "Proceed? [Y/n]: ",
        "prompt_cancelled": "Cancelled.",
        "prompt_press_enter": "Press ENTER to exit...",
        "prompt_platforms_header": "Optimize a specific platform?",
        "prompt_recycle":   "Empty recycle bin? [Y/n]: ",
        "prompt_temp":      "Delete temporary files? [Y/n]: ",
        "prompt_cache":     "Clean system cache? [Y/n]: ",
        "prompt_shaders":   "Clean shader caches? [Y/n]: ",
        "prompt_platform":  "  Optimize {plat}? ({count} games) [y/N]: ",
        "lbl_os":           "OS",
        "lbl_cpu":          "CPU",
        "lbl_cores":        "CORES",
        "lbl_ram":          "RAM",
        "lbl_gpu":          "GPU",
        "lbl_disk_free":    "FREE DISK",
        "lbl_disk_total":   "TOTAL DISK",
        "health_disk_low":  "⚠ LOW DISK ({pct:.0f}%)",
        "health_disk_ok":   "DISK OK ({pct:.0f}%)",
        "health_disk_good": "HEALTHY DISK ({pct:.0f}%)",
        "health_ram_low":   "⚠ LOW RAM ({ram} GB)",
        "health_sys_ok":    "SYSTEM OK",
        "game_count_plural":"({count} games)",
        "game_count_sing":  "({count} game)",
        "game_missing":     "(not detected)",
        "msg_quick_run":    "Running BOTH profile (quick)...",
        "msg_nothing":      "⚠  Nothing selected. Nothing to clean.",
        "msg_user_cancel":  "⚠  Operation cancelled by user.",
        "msg_success":      "✓ System optimized. Your PC is faster. ({m:02d}:{s:02d})",
        "msg_fail_cancel":  "⚠ Optimization cancelled after {m:02d}:{s:02d}.",
        "msg_fail_error":   "⚠ There were errors during cleanup. ({m:02d}:{s:02d})",
        "phase_trash":      "> Emptying recycle bin...",
        "phase_temp":       "> Deleting temporary files...",
        "phase_sys_cache":  "> Clearing system cache...",
        "phase_shaders":    "> Clearing shader caches (DirectX/NVIDIA/AMD)...",
        "phase_opt_plat":   "> Optimizing {plat}...",
        "phase_done":       "> COMPLETED",
        "phase_error":      "> ERROR: {e}",
        "sum_trash":        "Empty recycle bin",
        "sum_temp":         "Delete temporary files",
        "sum_cache":        "System cache",
        "sum_shaders":      "Shader caches",
        "sum_opt":          "Optimize {plat}",
        "linux_no_support": "\n  [ CLEANBOOST ]\n  Linux support discontinued.\n  Linux distributions manage caches, temp files and recycle bin\n  natively, making this kind of optimization unnecessary.\n",
    },
    "es": {
        "header_specs":     "═══ TUS ESPECIFICACIONES ═══",
        "header_games":     "═══ JUEGOS DETECTADOS ═══",
        "header_menu":      "═══ ¿QUÉ HACEMOS HOY? ═══",
        "header_summary":   "═══ RESUMEN ═══",
        "opt_1_title":      "OPTIMIZAR",
        "opt_1_desc":       "caché shaders + librerías\n        de juegos",
        "opt_2_title":      "LIMPIAR",
        "opt_2_desc":       "papelera + temporales + caché\n        del sistema",
        "opt_3_title":      "AMBAS",
        "opt_3_desc":       "full pass: shaders + sistema +\n        todas las plataformas",
        "menu_aux":         "Auxiliares: [v] ver specs  [q] salir",
        "prompt_choice":    "Elige una opción [1-3 / v / q]: ",
        "prompt_invalid":   "⚠  Opción no válida.",
        "prompt_proceed":   "¿Proceder? [Y/n]: ",
        "prompt_cancelled": "Cancelado.",
        "prompt_press_enter": "Pulsa ENTER para salir...",
        "prompt_platforms_header": "¿Optimizar alguna plataforma específica?",
        "prompt_recycle":   "¿Vaciar papelera? [Y/n]: ",
        "prompt_temp":      "¿Borrar archivos temporales? [Y/n]: ",
        "prompt_cache":     "¿Limpiar caché del sistema? [Y/n]: ",
        "prompt_shaders":   "¿Limpiar cachés de shaders? [Y/n]: ",
        "prompt_platform":  "  ¿Optimizar {plat}? ({count} juegos) [y/N]: ",
        "lbl_os":           "SO",
        "lbl_cpu":          "CPU",
        "lbl_cores":        "NUCLEOS",
        "lbl_ram":          "RAM",
        "lbl_gpu":          "GPU",
        "lbl_disk_free":    "DISCO LIBRE",
        "lbl_disk_total":   "DISCO TOTAL",
        "health_disk_low":  "⚠ DISCO BAJO ({pct:.0f}%)",
        "health_disk_ok":   "DISCO OK ({pct:.0f}%)",
        "health_disk_good": "DISCO SALUDABLE ({pct:.0f}%)",
        "health_ram_low":   "⚠ RAM BAJA ({ram} GB)",
        "health_sys_ok":    "SISTEMA OK",
        "game_count_plural":"({count} juegos)",
        "game_count_sing":  "({count} juego)",
        "game_missing":     "(no detectado)",
        "msg_quick_run":    "Ejecutando perfil AMBAS (rápido)...",
        "msg_nothing":      "⚠  Nada seleccionado. Nada que limpiar.",
        "msg_user_cancel":  "⚠  Operación cancelada por el usuario.",
        "msg_success":      "✓ Sistema optimizado. Tu PC está más rápido. ({m:02d}:{s:02d})",
        "msg_fail_cancel":  "⚠ Optimización cancelada después de {m:02d}:{s:02d}.",
        "msg_fail_error":   "⚠ Hubo errores durante la limpieza. ({m:02d}:{s:02d})",
        "phase_trash":      "> Vaciando papelera de reciclaje...",
        "phase_temp":       "> Borrando archivos temporales...",
        "phase_sys_cache":  "> Vaciando caché del sistema...",
        "phase_shaders":    "> Limpiando cachés de shaders (DirectX/NVIDIA/AMD)...",
        "phase_opt_plat":   "> Optimizando {plat}...",
        "phase_done":       "> COMPLETADO",
        "phase_error":      "> ERROR: {e}",
        "sum_trash":        "Vaciar papelera",
        "sum_temp":         "Borrar temporales",
        "sum_cache":        "Caché del sistema",
        "sum_shaders":      "Cachés de shaders",
        "sum_opt":          "Optimizar {plat}",
        "linux_no_support": "\n  [ CLEANBOOST ]\n  Soporte para Linux descontinuado.\n  Las distribuciones Linux gestionan sus cachés, archivos temporales\n  y papelera de forma nativa e independiente, haciendo innecesaria\n  esta optimización.\n",
    },
}


def get_locale(args: Optional[argparse.Namespace] = None) -> str:
    """Resuelve el idioma activo. Prioridad:
      1. ``args.lang`` (override via flag CLI ``--lang``).
      2. ``LC_ALL`` > ``LC_MESSAGES`` > ``LANG``.
      3. ``locale.getlocale()[0]`` (lo que el sistema reporta).
      4. Default ``"en"``.
    """
    # 1. override CLI
    if args is not None and getattr(args, "lang", None):
        v = args.lang.lower()[:2]
        if v in ("en", "es"):
            return v
    # 2. entorno
    for env in ("LC_ALL", "LC_MESSAGES", "LANG"):
        raw = os.environ.get(env)
        if not raw:
            continue
        # ``LANG=es_ES.UTF-8``` → ``es``
        v = raw.split(".", 1)[0].split("_", 1)[0].split("@", 1)[0].lower()[:2]
        if v in ("en", "es"):
            return v
    # 3. sistema
    try:
        loc = _locale.getlocale()[0]
        if loc:
            v = loc.split("_", 1)[0].lower()[:2]
            if v in ("en", "es"):
                return v
    except Exception:
        pass
    # 4. fallback
    return "en"


# Estado en tiempo de ejecución: el idioma activo. Se actualiza en ``main()``
# tras parsear args. Cualquier ``t()`` lee este valor.
_CURRENT_LANG: str = "en"


def set_lang(lang: str) -> None:
    """Inyecta el idioma en el módulo. Llamar UNA vez desde main() tras
    parsear args. ``lang`` debe ser ``"en"`` o ``"es"``."""
    global _CURRENT_LANG
    _CURRENT_LANG = lang if lang in ("en", "es") else "en"


def t(key: str, **kwargs) -> str:
    """Devuelve la cadena traducida en el idioma activo.
    Si la key no existe en el idioma actual, cae al inglés; si tampoco
    existe ahí, devuelve la key literal (defensa contra typos en strings).
    Acepta ``**kwargs`` para ``str.format(**kwargs)`` con placeholders
    como ``{count}``, ``{pct}``, ``{ram}``, ``{plat}``, ``{m}``, ``{s}``.
    """
    bucket = _STRINGS.get(_CURRENT_LANG, {})
    text = bucket.get(key)
    if text is None:
        text = _STRINGS.get("en", {}).get(key, key)
    if kwargs and isinstance(text, str):
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError):
            return text
    return text


# ============================================================================
# ESPECIFICACIONES DE PLATAFORMAS DE JUEGOS Y CACHÉS DE SHADERS
# ============================================================================
# Cada plataforma tiene rutas típicas de instalación por SO. El escaneo se
# hace en orden: si la primera ruta existe, se considera instalada y se
# cuentan los juegos (subcarpetas o steamapps/common). 'shader_paths' son
# subcarpetas dentro del install root que contienen cachés.

GAME_PLATFORMS = {
    "Steam": {
        "win": [r"C:\Program Files (x86)\Steam",
                r"C:\Program Files\Steam"],
        "darwin": ["~/Library/Application Support/Steam"],
        "shader_paths": ["shadercache", "appcache", "depotcache"],
        "count_subdir": "steamapps/common",
    },
    "Epic Games": {
        "win": [r"C:\Program Files\Epic Games"],
        "darwin": ["~/Library/Application Support/Epic"],
        "shader_paths": [],
        "count_subdir": "",
    },
    "Battle.net": {
        "win": [r"C:\Program Files (x86)\Battle.net",
                r"C:\ProgramData\Battle.net"],
        "darwin": [],
        "shader_paths": [],
        "count_subdir": "",
    },
    "GOG Galaxy": {
        "win": [r"C:\Program Files (x86)\GOG Galaxy\Games"],
        "darwin": ["~/Library/Application Support/GOG Galaxy/Games"],
        "shader_paths": [],
        "count_subdir": "",
    },
    "Minecraft": {
        "win": [r"%APPDATA%\.minecraft"],
        "darwin": ["~/Library/Application Support/minecraft"],
        "shader_paths": ["shaderpack-cache"],
        "count_subdir": "",
    },
    "Roblox": {
        # Launcher de Roblox Studio/Player legítimo (F2P, gestor oficial).
        # Las subcarpetas "logs" / "Downloads" / "http" acumulan cachés
        # que se regeneran en el próximo arranque; limpiarlas es seguro.
        "win": [r"%LOCALAPPDATA%\Roblox"],
        "darwin": ["~/Library/Roblox"],
        "shader_paths": ["logs", "Downloads", "http"],
        "count_subdir": "",
    },
}

# Cachés de shaders genéricos (sólo Windows y macOS). Soporte Linux
# eliminado: las distribuciones Linux gestionan sus cachés de forma
# nativa, por lo que CleanBoost ya no ofrece limpiarlas.
SHADER_CACHES = {
    "win": [
        ("DirectX Shader Cache",  r"%LOCALAPPDATA%\D3DSCache"),
        ("NVIDIA DXCache",        r"%LOCALAPPDATA%\NVIDIA\DXCache"),
        ("NVIDIA GLCache",        r"%LOCALAPPDATA%\NVIDIA\GLCache"),
        ("AMD DXCache",           r"%LOCALAPPDATA%\AMD\DXCache"),
    ],
    "darwin": [
        # macOS no tiene equivalentes a DirectX; sólo se incluye el cache
        # de Steam como destino legítimo.
        ("Steam shadercache", "~/Library/Application Support/Steam/shadercache"),
    ],
}


# ============================================================================
# FUNCIONES DE UTILIDAD (SO, LIMPIEZA DE DIRECTORIOS)
# ============================================================================
def get_os() -> str:
    p = platform.system().lower()
    if p.startswith("win"):
        return "windows"
    if p == "darwin":
        return "darwin"
    # Devolvemos "linux" para que main() pueda detectarlo y emitir un mensaje
    # informativo antes de abortar. Las funciones de limpieza ya NO incluyen
    # rutas o comandos específicos de Linux.
    return "linux"


def _expand_path(template: str) -> str:
    """Expande %VAR% en Windows y ~ en Unix. Combina ambas para cross-OS."""
    return os.path.expandvars(os.path.expanduser(template))


def _os_key() -> str:
    n = get_os()
    if n == "windows":
        return "win"
    if n == "darwin":
        return "darwin"
    # Linux ya no entra aquí en flujo normal (main() aborta antes). Se
    # devuelve "linux" defensivamente para que los ``.get(os_key, [])`` no
    # revienten; el resultado siempre será un conjunto vacío de rutas.
    return "linux"


# ============================================================================
# UTILIDADES DE COLOR ANSI (CLI / LINUX)
# ============================================================================
# Respetar NO_COLOR (https://no-color.org/) y TERM=dumb: implementamos como
# función para que cambios de entorno en runtime (e.g. piping tras import)
# se reflejen sin necesidad de re-importar.
def _no_color_enabled() -> bool:
    return (
        not sys.stdout.isatty()
        or os.environ.get("NO_COLOR") is not None
        or os.environ.get("TERM", "").lower() == "dumb"
    )


def ansi(text, *codes):
    """Envuelve `text` con códigos ANSI 256-color si la terminal lo soporta."""
    if not codes or _no_color_enabled():
        return text
    return f"\033[{';'.join(str(c) for c in codes)}m{text}\033[0m"


# Tema principal (blanco/azul/verde/gris) mapeado a códigos 256-color.
# Esquema simple, 4 colores, sin gradientes ni animaciones: pensado para
# máxima legibilidad en terminales de cualquier fondo. El verde marca
# éxito funcional; el azul marca avisos; el gris marca descripciones.
_THEME = {
    # Tema unificado blanco. Solo 4 colores en uso real:
    #   white  -> banners, headers, valores, botones, labels, progress messages, menu aux.
    #   blue   -> warnings: disco/RAM bajos, cancelaciones, errores, opciones invalidas.
    #   green  -> marca funcional OK mark, relleno del progress bar (visibilidad durante cleanup).
    #   gray   -> descripciones, sub-labels (jerarquia muda).
    "white":  (38, 5, 231, 1),  # bold + bright_white (ANSI 256-color code 231)
    "blue":   (38, 5, 75, 1),  # steel blue (warning) — reemplaza al amarillo anterior.  # bold + amarillo (warning)
    "green":  (38, 5, 46, 1),  # bold + verde brillante (acento funcional OK / progress) — ANSI 46 (true green, antes usaba #FFE600 gold)
    "gray":   (38, 5, 244),     # muted descriptions
}


def themed(text: str, theme_name: str) -> str:
    """Atajo: ``themed('CLEANBOOST', 'green')``."""
    return ansi(text, *_THEME.get(theme_name, ()))


def _empty_dir_contents(directory: str) -> int:
    """Vacía el contenido de un directorio sin eliminarlo. Robusto."""
    if not directory or not os.path.isdir(directory):
        return 0
    try:
        entries = list(os.scandir(directory))
    except (PermissionError, OSError):
        return 0
    removed = 0
    for entry in entries:
        try:
            if entry.is_file() or entry.is_symlink():
                os.unlink(entry.path); removed += 1
            elif entry.is_dir():
                shutil.rmtree(entry.path, ignore_errors=True)
                if not os.path.exists(entry.path):
                    removed += 1
        except (PermissionError, OSError, FileNotFoundError):
            continue
    return removed


def empty_recycle_bin(stop_flag: threading.Event = None) -> None:
    """Vacía la papelera del SO (sólo Windows y macOS)."""
    if stop_flag is not None and stop_flag.is_set():
        return
    os_name = get_os()
    if os_name == "windows":
        try:
            subprocess.run(
                ["powershell", "-NoProfile",
                 "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                capture_output=True, timeout=30, check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
    elif os_name == "darwin":
        _empty_dir_contents(str(Path.home() / ".Trash"))
    # En Linux main() ya abortó antes de llegar aquí; no hay rama.


def clear_temp_files(stop_flag: threading.Event = None) -> None:
    """Borra archivos temporales del usuario (sólo Windows y macOS)."""
    if stop_flag is not None and stop_flag.is_set():
        return
    os_name = get_os()
    if os_name == "windows":
        candidates = [os.environ.get("TEMP", ""), os.environ.get("TMP", "")]
    elif os_name == "darwin":
        candidates = [os.environ.get("TMPDIR", "")]
    else:
        # main() aborta en Linux; defensivo, no se hace nada.
        candidates = []
    for d in candidates:
        if stop_flag is not None and stop_flag.is_set():
            return
        if d and os.path.isdir(d):
            _empty_dir_contents(d)


def clear_system_cache(stop_flag: threading.Event = None) -> None:
    """Vacía caché del sistema (sólo Windows y macOS)."""
    if stop_flag is not None and stop_flag.is_set():
        return
    os_name = get_os()
    home = Path.home()
    cache_dirs = []
    if os_name == "darwin":
        c = home / "Library" / "Caches"
        if c.exists(): cache_dirs.append(c)
    elif os_name == "windows":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            for sub in (r"Microsoft\Windows\INetCache",
                        r"Microsoft\Windows\Explorer"):
                p = Path(local) / sub
                if p.exists(): cache_dirs.append(p)
    # En Linux main() ya abortó antes; no hay rama.
    for cd in cache_dirs:
        if stop_flag is not None and stop_flag.is_set():
            return
        if cd.exists():
            _empty_dir_contents(str(cd))


# ============================================================================
# DETECCIÓN DE ESPECIFICACIONES DEL SISTEMA
# ============================================================================
def get_system_specs() -> dict:
    """Devuelve dict con specs del sistema. Defensivo: si algo falla,
    retorna 'N/A' / 0 en lugar de lanzar excepción."""
    specs = {
        "os": get_os(),
        "cpu_count": os.cpu_count() or 1,
        "cpu_name": "N/A",
        "ram_gb": 0,
        "disk_free_gb": 0,
        "disk_total_gb": 0,
        "gpu_name": "N/A",
    }
    os_name = get_os()

    # Memoria y disco via shutil (cross-platform, stdlib puro)
    try:
        usage = shutil.disk_usage(os.path.abspath(os.sep))
        specs["disk_total_gb"] = round(usage.total / 1e9)
        specs["disk_free_gb"] = round(usage.free / 1e9)
    except Exception:
        pass

    # CPU y GPU via subprocess (defensivo). Comandos específicos por SO.
    try:
        if os_name == "windows":
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                specs["cpu_name"] = r.stdout.strip().split("\n")[0][:60]
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "[math]::Round((Get-CimInstance Win32_ComputerSystem)."
                 "TotalPhysicalMemory / 1GB)"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                try: specs["ram_gb"] = int(float(r.stdout.strip()))
                except ValueError: pass
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_VideoController).Name"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0 and r.stdout.strip():
                specs["gpu_name"] = r.stdout.strip().split("\n")[0][:60]
        elif os_name == "darwin":
            try:
                r = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0 and r.stdout.strip():
                    specs["cpu_name"] = r.stdout.strip().split("\n")[0][:60]
            except (FileNotFoundError, OSError):
                pass
            try:
                r = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True, timeout=10,
                )
                if r.returncode == 0:
                    try: specs["ram_gb"] = round(int(r.stdout.strip()) / 1e9)
                    except ValueError: pass
            except (FileNotFoundError, OSError):
                pass
            try:
                r = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True, text=True, timeout=15,
                )
                if r.returncode == 0:
                    for line in r.stdout.split("\n"):
                        if "Chipset Model:" in line:
                            specs["gpu_name"] = line.split(":", 1)[1].strip()[:60]
                            break
            except (FileNotFoundError, OSError):
                pass
        # Linux: la app ya abortó en main() antes de llegar aquí. Si alguien
        # invoca esta función en REPL, los valores por defecto (cpu_name
        # 'N/A', ram_gb 0, gpu_name 'N/A') son seguros y nítidos.
    except Exception:
        pass

    return specs


# ============================================================================
# DETECCIÓN DE JUEGOS INSTALADOS
# ============================================================================
def detect_games() -> list:
    """Escanea las bibliotecas de juegos instaladas. Devuelve una lista de
    dicts {name, available, count, path, subdirs_cleared}."""
    os_key = _os_key()
    results = []
    for name, info in GAME_PLATFORMS.items():
        path_templates = info.get(os_key, [])
        install_path = None
        count = 0
        for tmpl in path_templates:
            p = _expand_path(tmpl)
            if os.path.isdir(p):
                install_path = p
                try:
                    base = Path(p)
                    if name == "Steam":
                        # Steam cuenta juegos por subcarpetas en steamapps/common
                        common = base / "steamapps" / "common"
                        if common.is_dir():
                            count = sum(1 for x in common.iterdir() if x.is_dir())
                        else:
                            count = 0
                    else:
                        # Genérico: subcarpetas que NO empiecen con '.'
                        count = sum(
                            1 for x in base.iterdir()
                            if x.is_dir() and not x.name.startswith(".")
                        )
                except (PermissionError, OSError):
                    count = 0
                break
        results.append({
            "name": name,
            "available": install_path is not None,
            "count": count,
            "path": install_path,
        })
    return results


def optimize_platform(platform_name: str,
                      stop_flag: threading.Event = None) -> int:
    """Limpia las cachés y subcarpetas asociadas a una plataforma de juego.
    Retorna el número de elementos eliminados."""
    if stop_flag is not None and stop_flag.is_set():
        return 0
    info = GAME_PLATFORMS.get(platform_name)
    if not info:
        return 0
    os_key = _os_key()
    install_path = None
    for tmpl in info.get(os_key, []):
        p = _expand_path(tmpl)
        if os.path.isdir(p):
            install_path = p
            break
    if not install_path:
        return 0
    removed = 0
    base = Path(install_path)
    for sub in info.get("shader_paths", []):
        if stop_flag is not None and stop_flag.is_set():
            return removed
        sub_path = base / sub
        if sub_path.exists():
            removed += _empty_dir_contents(str(sub_path))
    return removed


def optimize_shader_caches(stop_flag: threading.Event = None) -> int:
    """Vacía las cachés de shaders genéricas (DirectX, NVIDIA, AMD, Mesa)."""
    if stop_flag is not None and stop_flag.is_set():
        return 0
    os_key = _os_key()
    removed = 0
    for label, tmpl in SHADER_CACHES.get(os_key, []):
        if stop_flag is not None and stop_flag.is_set():
            return removed
        p = _expand_path(tmpl)
        if os.path.isdir(p):
            removed += _empty_dir_contents(p)
    return removed


def run_full_cleanup(stop_flag, status_cb, finished_cb, *,
                     selected_platforms=None, clean_shaders=True,
                     clean_recycle=True, clean_temp=True,
                     clean_cache=True):
    """Orquesta todas las fases. Ejecuta en un hilo secundario. Si recibe
    un _PhaseTracker en stop_flag, llama a tracker.advance() en cada fase
    para alimentar la barra de progreso.

    Las fases ``clean_recycle``, ``clean_temp``, ``clean_cache`` y
    ``clean_shaders`` son kwargs opcionales (default True). Cuando una
    fase está desactivada: se OMITE por completo — ``status_cb`` no se
    llama, la función de limpieza no se ejecuta, y el tracker NO avanza
    en esa fase. Por tanto, ``total_phases`` pasado al ``_PhaseTracker``
    debe coincidir con el conteo de fases habilitadas
    (``sum([clean_X]) + len(platforms)`` es la fórmula correcta).
    """
    selected_platforms = selected_platforms or []
    # Si stop_flag es None, crear uno nunca seteado para que los chequeos
    # stop_flag.is_set() en cada fase no rompan con AttributeError.
    if stop_flag is None:
        stop_flag = threading.Event()
    tracker = stop_flag if isinstance(stop_flag, _PhaseTracker) else None
    try:
        # Fase 1: papelera (opcional)
        if clean_recycle:
            status_cb(t("phase_trash"))
            if tracker: tracker.advance()
            empty_recycle_bin(stop_flag)
        else:
            pass
        if stop_flag.is_set():
            finished_cb(False, cancelled=True); return

        # Fase 2: temporales (opcional)
        if clean_temp:
            status_cb(t("phase_temp"))
            if tracker: tracker.advance()
            clear_temp_files(stop_flag)
        else:
            pass
        if stop_flag.is_set():
            finished_cb(False, cancelled=True); return

        # Fase 3: caché sistema (opcional)
        if clean_cache:
            status_cb(t("phase_sys_cache"))
            if tracker: tracker.advance()
            clear_system_cache(stop_flag)
        else:
            pass
        if stop_flag.is_set():
            finished_cb(False, cancelled=True); return

        # Fase 4: cachés de shaders (opcional)
        if clean_shaders:
            status_cb(t("phase_shaders"))
            if tracker: tracker.advance()
            optimize_shader_caches(stop_flag)
        else:
            pass
        if stop_flag.is_set():
            finished_cb(False, cancelled=True); return

        # Fase 5: juegos seleccionados
        for plat in selected_platforms:
            if stop_flag.is_set():
                finished_cb(False, cancelled=True); return
            status_cb(t("phase_opt_plat", plat=plat))
            if tracker: tracker.advance()
            optimize_platform(plat, stop_flag)

        time.sleep(0.3)
        # advance "marcador" tras COMPLETADO: por diseño el counter puede
        # exceder total_phases en 1 (las UIs lo clampean con min(100,…)).
        if tracker: tracker.advance()
        status_cb(t("phase_done"))
        finished_cb(True)
    except (OSError, subprocess.SubprocessError, FileNotFoundError) as e:
        status_cb(t("phase_error", e=e))
        finished_cb(False)

# ============================================================================
# Helper: rastreador de fases para alimentar la barra de progreso.
# Envuelve un threading.Event y avanza el progreso al inicio de cada fase.
# ============================================================================
class _PhaseTracker:
    """Envuelve un threading.Event para que run_full_cleanup pueda informar
    progreso a la UI al inicio de cada fase. La cancelación del usuario NO
    emite progreso (sería contradictorio reportar avance mientras el
    usuario intenta detener)."""

    def __init__(self, real_flag, total_phases, current_counter,
                 progress_cb=None):
        self._flag = real_flag
        self._total = max(1, total_phases)
        self._current = current_counter
        self._cb = progress_cb

    def is_set(self):
        return self._flag.is_set()

    def set(self):
        """Cancelación: solo delega, NO emite progreso."""
        self._flag.set()

    def clear(self):
        self._flag.clear()

    def advance(self):
        """Llamado por run_full_cleanup al iniciar cada fase."""
        self._current[0] += 1
        pct = min(100, 100 * self._current[0] // self._total)
        if self._cb is not None:
            self._cb(pct)


# ============================================================================
# INTERFAZ DE TERMINAL — WINDOWS / macOS (TUI)
# ============================================================================
# Esta es la ÚNICA interfaz disponible. Soporte Linux eliminado: las
# distribuciones Linux gestionan sus cachés de forma nativa, por lo que
# CleanBoost ya no ofrece limpiar en ese SO.
#
# Banner ASCII con caracteres Unicode box-drawing. Legible también sin color
# gracias a un buen contraste fondo/tinta — los temas degradan con naturalidad
# si el locale no es UTF-8 (los '?' en bordes no afectan el mensaje principal).
_CLI_BANNER = (
    "\n"
    " ████ ██    █████  ███  ██  █ ████   ███   ███   ████ █████\n"
    "██    ██    ██    ██  █ ███ █ ██  █ ██  █ ██  █ ██      ██\n"
    "██    ██    ██    ██  █ █████ ██  █ ██  █ ██  █ ██      ██\n"
    "██    ██    ████  █████ ██ ██ ████  ██  █ ██  █  ███    ██\n"
    "██    ██    ██    ██  █ █  ██ ██  █ ██  █ ██  █    ██   ██\n"
    "██    ██    ██    ██  █ █  ██ ██  █ ██  █ ██  █    ██   ██\n"
    " ████ █████ █████ ██  █ █  ██ ████   ███   ███  ████    ██\n"
)
# Banner minimalista: SOLO el texto "CLEANBOOST" en ASCII art blocky de
# 7 filas × 5 columnas/letra, con formas robustas y fácilmente reconocibles
# (cada letra tiene cuerpo y base coherentes, sin diagonales artificiosas).
# Color: blanco (ANSI 256-color code 231 + bold) para máximo contraste sobre
# fondo oscuro de la terminal.


class CleanBoostCLI:
    """Interfaz de línea de comandos para Windows y macOS.

    Es la única interfaz disponible: soporte Linux eliminado. Reutiliza
    todas las funciones de detección y limpieza ya definidas arriba
    (get_system_specs, detect_games, run_full_cleanup, etc.). No requiere
    servidor de display, no añade dependencias externas y respeta las
    convenciones NO_COLOR y TERM=dumb.

    Diseñada para terminales UTF-8 con ancho de al menos 60 columnas. En
    terminales más estrechas el banner puede truncarse visualmente pero la
    legibilidad del texto se mantiene.
    """

    PROGRESS_BAR_WIDTH = 28  # bloques para la barra de progreso (28 chars)

    def __init__(self) -> None:
        self.specs = get_system_specs()
        self.games = detect_games()
        self.platform_vars = {g["name"]: False for g in self.games}
        self.shaders_var = True
        self.recycle_var = True
        self.temp_var = True
        self.cache_var = True

        # Estado en tiempo de ejecución.
        self.is_running = False
        self.stop_flag = threading.Event()
        self.start_time = 0.0
        self._phase_total = 0
        self._phase_counter = [0]   # mutado por _PhaseTracker; legible desde
                                    # el hilo de animación y el status_cb.
        self._status_line = "Iniciando"

    # ---------------------- presentación ----------------------
    def _banner(self) -> None:
        for line in _CLI_BANNER.splitlines():
            print(themed(line, "white"))

    def _specs_panel(self) -> None:
        s = self.specs
        health = []
        if s["disk_total_gb"] > 0:
            pct = 100 * s["disk_free_gb"] / s["disk_total_gb"]
            if pct < 15:
                health.append(themed(t("health_disk_low", pct=pct), "blue"))
            elif pct < 30:
                health.append(themed(t("health_disk_ok", pct=pct), "white"))
            else:
                health.append(themed(t("health_disk_good", pct=pct), "white"))
        if s["ram_gb"] > 0 and s["ram_gb"] < 8:
            health.append(themed(t("health_ram_low", ram=s["ram_gb"]), "blue"))
        if not health:
            health.append(themed(t("health_sys_ok"), "white"))

        rows = [
            (t("lbl_os"),         s["os"].upper()),
            (t("lbl_cpu"),        s["cpu_name"] or "N/A"),
            (t("lbl_cores"),      str(s["cpu_count"])),
            (t("lbl_ram"),        f"{s['ram_gb']} GB"),
            (t("lbl_gpu"),        s["gpu_name"] or "N/A"),
            (t("lbl_disk_free"),  f"{s['disk_free_gb']} GB"),
            (t("lbl_disk_total"), f"{s['disk_total_gb']} GB"),
        ]
        print()
        print(themed("  " + t("header_specs"), "white"))
        for label, value in rows:
            print(
                "  "
                + themed(f"{label:<14}", "gray")
                + ": "
                + themed(value, "white")
            )
        print("  " + " │ ".join(health))

    def _games_panel(self) -> None:
        print()
        print(themed("  " + t("header_games"), "white"))
        for g in self.games:
            if g["available"]:
                mark = themed("✔", "green")
                # Pluraliza correctamente: "1 juego" vs "5 juegos".
                count_key = "game_count_sing" if g["count"] == 1 else "game_count_plural"
                count_txt = t(count_key, count=g["count"])
                line = f"  {mark} {g['name']} {themed(count_txt, 'gray')}"
            else:
                mark = themed("✗", "blue")
                line = f"  {mark} {g['name']} {themed(t('game_missing'), 'gray')}"
            print(line)
        print()

    def _print_menu(self) -> None:
        """Dibuja el menú principal de 3 botones grandes. Estética coherente
        con el banner: bordes ╔══╗, contraste fondo/tinta fuerte, números
        rself en oro brillante.
        """
        print()
        print(themed("  " + t("header_menu"), "white"))
        print()
        rows = [
            ("1", t("opt_1_title"), t("opt_1_desc")),
            ("2", t("opt_2_title"), t("opt_2_desc")),
            ("3", t("opt_3_title"), t("opt_3_desc")),
        ]
        # Tres cajas alineadas, separadas por espacios. Cada caja mide 24
        # caracteres de ancho; el número se imprime aislado en la cabecera
        # para que sea fácil de apuntar.
        for num, label, desc in rows:
            num_styled = themed(f" [{num}] ", "white")
            head = f"   {num_styled}{themed(label, 'white')}"
            print(head)
            for line in desc.split("\n"):
                print(themed(f"        {line.strip()}", "gray"))
            print()
        # Acciones auxiliares, fuera de las cajas para no mezclarlas.
        print(themed("  " + t("menu_aux"), "white"))
        print()

    # Mapa de acción por botón: traduce (1/2/3) a kwargs de run_full_cleanup.
    # Centralizado para que los tests puedan verificarlo independientemente
    # de cualquier UI. Si en el futuro se añaden más botones, basta con
    # extender este dict.
    _ACTION_MAP = {
        "1": {  # OPTIMIZACIÓN: gaming & shaders; no toca papelera/temp.
            "selected_platforms_sentinel": "all_available",
            "clean_shaders":  True,
            "clean_recycle":  False,
            "clean_temp":     False,
            "clean_cache":    False,
        },
        "2": {  # LIMPIEZA: sistema; sin tocar librerías de juego.
            "selected_platforms_sentinel": "none",
            "clean_shaders":  False,
            "clean_recycle":  True,
            "clean_temp":     True,
            "clean_cache":    True,
        },
        "3": {  # AMBAS: full pass.
            "selected_platforms_sentinel": "all_available",
            "clean_shaders":  True,
            "clean_recycle":  True,
            "clean_temp":     True,
            "clean_cache":    True,
        },
    }

    def _resolve_action(self, button: str) -> dict:
        """Convierte ``button`` ('1'/'2'/'3') en kwargs listos para
        ``run_full_cleanup``. Saca los nombres reales de plataformas
        detectados para que el caller los escriba en la selección.

        Importante: NO mutamos ``_ACTION_MAP[button]`` (es una constante de
        clase compartida entre instancias y entre invocaciones). Construimos
        un dict nuevo a partir de la entrada del mapa, leyendo el sentinel
        con ``.get()`` y descartándolo sin tocar el original.
        """
        template = self._ACTION_MAP[button]
        sentinel = template["selected_platforms_sentinel"]
        cfg = {k: v for k, v in template.items() if k != "selected_platforms_sentinel"}
        if sentinel == "all_available":
            cfg["selected_platforms"] = [
                g["name"] for g in self.games if g["available"]
            ]
        else:
            cfg["selected_platforms"] = []
        return cfg

    # ---------------------- prompts ----------------------
    def _ask(self, prompt: str) -> str:
        return input(themed("> ", "white") + prompt).strip()

    def _ask_yn(self, question: str, default: bool = True) -> bool:
        suffix = "[Y/n]" if default else "[y/N]"
        ans = self._ask(f"{question} {suffix}: ").lower()
        if ans in ("y", "yes", "s", "si", "sí"):
            return True
        if ans in ("n", "no"):
            return False
        return default

    # ---------------------- flujo principal ----------------------
    def run(self) -> None:
        """Punto de entrada de la CLI. Flujo de 3 botones."""
        try:
            self._banner()
            self._specs_panel()
            self._games_panel()

            while True:
                self._print_menu()
                raw = self._ask("Elige una opción [1-3 / v / q]: ").lower()
                if raw in ("q", "4", "exit", "quit"):
                    self._goodbye()
                    return
                if raw in ("v", "specs", "5"):
                    self._specs_panel()
                    self._games_panel()
                    continue
                if raw in self._ACTION_MAP:
                    self._confirm_and_run(self._resolve_action(raw))
                    return
                print(themed("  ⚠  Opción no válida.", "blue"))
        except (KeyboardInterrupt, EOFError):
            print()
            self._goodbye(cancelled=True)
            sys.exit(130)

    def run_quick(self) -> None:
        """Modo `--quick`: salta banner+specs+confirmación y ejecuta el
        perfil "AMBAS" directamente. Pensado para invocación desde wrappers
        (doble-clic) o desde el daemon semanal."""
        self._banner()
        cfg = self._resolve_action("3")
        # Sin prompt: ejecutamos directamente. El usuario ya hizo doble-clic
        # o vino del daemon, así que el consentimiento está implícito.
        print(themed("  " + t("msg_quick_run"), "white"))
        self._run_cleanup(**cfg)

    def _goodbye(self, cancelled: bool = False) -> None:
        if cancelled:
            print(themed("  " + t("msg_user_cancel"), "blue"))
        else:
            print()
            print(themed("  ◆  CLEANBOOST  ◆", "white"))
            print()

    # ---------------------- “Limpieza completa” ----------------------
    def _gather_full_selection(self) -> dict:
        return {
            "selected_platforms": [
                g["name"] for g in self.games if g["available"]
            ],
            "clean_shaders": self.shaders_var,
            "clean_recycle": self.recycle_var,
            "clean_temp": self.temp_var,
            "clean_cache": self.cache_var,
        }

    # ---------------------- “Limpieza personalizada” ----------------------
    def _custom_selection(self) -> None:
        # ``t()`` resuelve los prompts al idioma activo. Si el usuario corre
        # con ``--lang=en``, todas las preguntas aparecen en inglés.
        self.recycle_var = self._ask_yn(t("prompt_recycle"), default=True)
        self.temp_var   = self._ask_yn(t("prompt_temp"), default=True)
        self.cache_var  = self._ask_yn(t("prompt_cache"), default=True)
        self.shaders_var = self._ask_yn(t("prompt_shaders"), default=True)
        print()
        print(themed("  " + t("prompt_platforms_header"), "gray"))
        for g in self.games:
            if g["available"]:
                count_key = "game_count_sing" if g["count"] == 1 else "game_count_plural"
                count_txt = t(count_key, count=g["count"])
                # ``prompt_platform`` ya lleva el sufijo "[y/N]: " en la tabla.
                count_key = "prompt_platform_sing" if g["count"] == 1 else "prompt_platform_plural"
                ok = self._ask_yn(
                    t(count_key, plat=g["name"], count=g["count"]),
                    default=False,
                )
                self.platform_vars[g["name"]] = ok

    def _gather_custom_selection(self) -> dict:
        selected = [
            name for name, on in self.platform_vars.items() if on
        ]
        return {
            "selected_platforms": selected,
            "clean_shaders": self.shaders_var,
            "clean_recycle": self.recycle_var,
            "clean_temp": self.temp_var,
            "clean_cache": self.cache_var,
        }

    # ---------------------- resumen + ejecución ----------------------
    def _confirm_and_run(self, selection: dict) -> None:
        selected = selection["selected_platforms"]
        any_selected = (
            selection["clean_recycle"]
            or selection["clean_temp"]
            or selection["clean_cache"]
            or selection["clean_shaders"]
            or bool(selected)
        )
        print()
        print(themed("  " + t("header_summary"), "white"))
        for label_key, on in [
            ("sum_trash",   selection["clean_recycle"]),
            ("sum_temp",    selection["clean_temp"]),
            ("sum_cache",   selection["clean_cache"]),
            ("sum_shaders", selection["clean_shaders"]),
        ]:
            mark = themed("✔", "green") if on else themed("✗", "gray")
            print(f"  {mark} {t(label_key)}")
        for name in selected:
            mark = themed("✔", "green")
            print(f"  {mark} {t('sum_opt', plat=name)}")

        if not any_selected:
            print(themed("  " + t("msg_nothing"), "blue"))
            return
        if not self._ask_yn(t("prompt_proceed"), default=True):
            print(themed("  " + t("prompt_cancelled"), "blue"))
            return
        self._run_cleanup(**selection)

    def _run_cleanup(self, *, selected_platforms, clean_shaders,
                     clean_recycle, clean_temp, clean_cache) -> None:
        """Lanza la limpieza en un hilo y anima una barra inline de progreso.

        Comportamiento según el destino:
        * TTY con color:  barra inline con spinner (se redibuja con ``\\r``).
        * No-TTY / NO_COLOR: cada fase se imprime como línea separada,
          apta para logs piped sin ensuciar con retornos de carro.
        """
        self.is_running = True
        self.stop_flag = threading.Event()
        self.start_time = time.time()
        self._phase_counter[0] = 0

        total_phases = sum(
            [clean_recycle, clean_temp, clean_cache, clean_shaders]
        ) + len(selected_platforms)
        self._phase_total = max(1, total_phases)        # El _PhaseTracker muta self._phase_counter al inicio de cada fase.
        # No necesitamos el callback (None) porque el hilo animador lee
        # directamente self._phase_counter. Esto evita races y deja una
        # sola fuente de verdad para el avance.
        self._tracker = _PhaseTracker(
            self.stop_flag,
            total_phases,
            self._phase_counter,
            None,
        )

        def on_status(msg: str) -> None:
            self._status_line = msg.lstrip("> ").strip()
            if _no_color_enabled():
                # Modo log (pipe / NO_COLOR): una línea por fase, sin \r.
                step = self._phase_counter[0]
                print(
                    f"  [paso {step}/{total_phases}] "
                    f"{self._status_line}",
                    flush=True,
                )

        def on_done(success: bool, cancelled: bool = False) -> None:
            # IMPORTANTE: escribir _last_result ANTES de bajar is_running.
            # El hilo main observa is_running en un while-loop; si lo
            # escribimos primero este, garantiza que cuando main despierte
            # y salga del loop, _last_result ya está actualizado.
            self._last_result = (success, cancelled)
            self.is_running = False

        worker = threading.Thread(
            target=run_full_cleanup,
            kwargs=dict(
                stop_flag=self._tracker,
                status_cb=on_status,
                finished_cb=on_done,
                selected_platforms=selected_platforms,
                clean_shaders=clean_shaders,
                clean_recycle=clean_recycle,
                clean_temp=clean_temp,
                clean_cache=clean_cache,
            ),
            daemon=True,
        )
        worker.start()

        # Animar barra inline sólo si la terminal soporta colores y es TTY.
        if not _no_color_enabled():
            self._animate_progress()
        while self.is_running:
            time.sleep(0.05)

        worker.join(timeout=0.1)
        # El cursor queda al final de la línea escrita por la barra;
        # un newline garantiza que el siguiente print() baje a línea nueva.
        if not _no_color_enabled():
            print()
        success, cancelled = self._last_result
        self._finish(success=success, cancelled=cancelled)

    def _animate_progress(self) -> None:
        """Hilo animator que redibuja la barra inline hasta que el worker
        termine. Lee ``self._phase_counter`` (mutado por ``_PhaseTracker``)
        para calcular el porcentaje.
        """
        spinner_states = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
        idx = 0
        while self.is_running:
            try:
                pct = (
                    100 * self._phase_counter[0]
                    // max(1, self._phase_total)
                )
                sys.stdout.write(
                    self._render_bar(
                        pct, spinner_states[idx % len(spinner_states)]
                    )
                )
                sys.stdout.flush()
            except (OSError, ValueError):
                # stdout cerrado (p.ej. ctrl-Z en pipe). Salir sin romper.
                return
            idx += 1
            time.sleep(0.10)

        # Pintar 100% una vez al final para que el usuario vea cierre claro
        try:
            sys.stdout.write(self._render_bar(100, "✓"))
            sys.stdout.flush()
        except (OSError, ValueError):
            return

    def _render_bar(self, percent: int, spinner: str) -> str:
        pct = max(0, min(100, int(percent)))
        filled = pct * self.PROGRESS_BAR_WIDTH // 100
        empty = self.PROGRESS_BAR_WIDTH - filled
        bar = "█" * filled + "░" * empty
        bar_styled = themed("[" + bar + "]", "green")
        pct_styled = themed(f" {pct:3d}%", "white")
        msg = self._status_line or "Iniciando"
        # \033[K limpia hasta fin de línea para evitar residuos de frames
        # anteriores. \r posiciona el cursor al inicio de la línea.
        return (
            "\r\033[K"
            + "  "
            + bar_styled
            + pct_styled
            + f" {spinner} "
            + themed(msg, "white")
        )

    def _finish(self, success: bool, cancelled: bool) -> None:
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        m, s = divmod(elapsed, 60)
        if cancelled:
            print(themed(
                t("msg_fail_cancel", m=m, s=s),
                "blue",
            ))
        elif success:
            print(themed(
                t("msg_success", m=m, s=s),
                "white",
            ))
        else:
            print(themed(
                t("msg_fail_error", m=m, s=s),
                "blue",
            ))


# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================
# (Mensaje de rechazo para Linux eliminado — usar ``t("linux_no_support")``
# desde ``main()`` para mantener el texto dentro del dict i18n.)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Parser CLI. Flags soportados:
    * ``--version``           imprime versión + sale
    * ``--quick``             ejecuta perfil AMBAS sin prompts (wrapper-friendly)
    * ``--enable-daemon``     crea el servicio periódico (launchd/systemd/Task)
    * ``--disable-daemon``    elimina el servicio periódico
    * ``--daemon-status``     describe el estado actual del daemon
    * ``--lang=en|es``        override del idioma (auto-detección por defecto)
    """
    p = argparse.ArgumentParser(
        prog="cleanboost",
        description="CleanBoost is fast, simple, 100% free terminal software that optimizes your system and detects games.",
        add_help=True,
    )
    p.add_argument("--version", action="store_true",
                   help="print version and exit")
    p.add_argument("--quick", action="store_true",
                   help="run BOTH profile without prompts")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--enable-daemon",  action="store_true",
                   help="install weekly reminder service")
    g.add_argument("--disable-daemon", action="store_true",
                   help="remove weekly reminder service")
    g.add_argument("--daemon-status",  action="store_true",
                   help="describe daemon current state")
    p.add_argument("--lang", choices=("en", "es"),
                   help="force language override (default: auto-detect from locale)")
    return p


def main(argv: Optional[list] = None) -> None:
    """Punto de entrada único. Despacha por flags → acción; sin flags → CLI 3 botones."""
    args = _build_arg_parser().parse_args(argv)
    # Activar el idioma ANTES de cualquier salida para que ``t()`` funcione
    # en mensajes (incluso el rechazo cortés de Linux).
    set_lang(get_locale(args))

    # Linux → rechazo cortés; los flags de daemon tampoco tienen sentido ahí.
    if get_os() == "linux":
        print(t("linux_no_support"), file=sys.stderr)
        sys.exit(0)

    # --- Meta-flags (no dependen de la plataforma) ---
    if args.version:
        print(f"cleanboost {__version__}")
        sys.exit(0)

    # --- Daemon ops: dispatch al módulo daemon ---
    if args.enable_daemon or args.disable_daemon or args.daemon_status:
        daemon.run(
            enable=args.enable_daemon,
            disable=args.disable_daemon,
            status=args.daemon_status,
        )
        sys.exit(0)

    # --- Flujo CLI normal ---
    try:
        if args.quick:
            CleanBoostCLI().run_quick()
        else:
            CleanBoostCLI().run()
    except KeyboardInterrupt:
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[CLEANBOOST] Error fatal: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
