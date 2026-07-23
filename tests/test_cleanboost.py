"""
test_cleanboost.py — Tests no-destructivos para CLEANBOOST
==========================================================
Estrategia de testing:
- Los tests NUNCA tocan la papelera real ni /tmp del sistema.
- Las funciones de borrado reales (_empty_dir_contents) se mockean
  para verificar qué RUTAS se derivan en cada SO, sin realmente
  abrir ni borrar archivos. Esto evita conflictos con paths
  especiales (.Trash, /var/folders/...) en macOS.
- Section 3 IS un test de integración real con un tempdir aislado,
  para validar que _empty_dir_contents funciona correctamente.

Cobertura:
1. main.py importa sin errores de sintaxis o de imports.
2. get_os() devuelve un SO conocido.
3. _empty_dir_contents() borra contenido preservando el directorio
   (test de integración real con tempdir aislado).
4. Las funciones DERIVAN las rutas correctas por SO (con mocks).
5. run_full_cleanup() respeta el stop_flag cooperativo en cada fase.
6. Errores de subprocess (TimeoutExpired, FileNotFoundError) no rompen.
7. Estructura de la clase UI y constantes de tema.
"""

import io
import os
import subprocess as _subprocess
import sys
import tempfile
import threading
import importlib.util
import argparse
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from unittest.mock import patch, MagicMock

# Forzar idioma español para TODA la suite de tests. Esto preserva compat con
# las aserciones legacy que validan strings literales en español ("TUS
# ESPECIFICACIONES", "DISCO BAJO", etc.) tras el refactor de i18n. La app
# en producción detecta el locale automáticamente desde ``LANG``/``LC_ALL``.
os.environ["LC_ALL"] = "es_ES.UTF-8"
# ``reconfigure`` no existe en stdout cuando se corre bajo capture; basta con
# setear las variables antes de que ``main.py`` se importe.


# ---------------------------------------------------------------------------
# Helpers de prueba para TTY/NO_COLOR
# ---------------------------------------------------------------------------
class _FakeTTY:
    """Mock de sys.stdout que reporta isatty() == True y permite write()."""

    def isatty(self):
        return True

    def write(self, s):
        return len(s)

    def flush(self):
        pass

    def __getattr__(self, name):
        # Cualquier otro atributo que pida el código (encoding, mode, etc.)
        # se devuelve de forma inocua.
        return lambda *a, **k: 0


class _NonTTY:
    """Mock de sys.stdout que reporta isatty() == False (p. ej. pipe a file)."""

    def isatty(self):
        return False

    def write(self, s):
        return len(s)

    def flush(self):
        pass

    def __getattr__(self, name):
        return lambda *a, **k: 0


# ---------------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------------
PASS = "✓"
FAIL = "✗"
results = []


def section(title):
    print()
    print("─" * 60)
    print(f"  {title}")
    print("─" * 60)


def check(name, ok, detail=""):
    icon = PASS if ok else FAIL
    line = f"  {icon} {name}"
    if detail:
        line += f"  — {detail}"
    print(line)
    results.append((name, ok, detail))


# ---------------------------------------------------------------------------
# Cargar main.py como módulo
# ---------------------------------------------------------------------------
section("1. Carga del módulo")

try:
    spec = importlib.util.spec_from_file_location("main_module", "main.py")
    main_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_mod)
    check("main.py importa sin errores", True)
except Exception as e:
    check("main.py importa sin errores", False, f"{type(e).__name__}: {e}")
    print()
    print("ABORTANDO: no se puede continuar sin importar el módulo.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Test 2: get_os()
# ---------------------------------------------------------------------------
section("2. Detección de sistema operativo")

os_result = main_mod.get_os()
check(
    "get_os() devuelve un SO conocido",
    os_result in ("windows", "darwin", "linux"),
    f"devuelto: '{os_result}'",
)


# ---------------------------------------------------------------------------
# Test 3: _empty_dir_contents() — INTEGRACIÓN REAL sobre tempdir aislado
# ---------------------------------------------------------------------------
section("3. _empty_dir_contents (integración real aislada)")

# 3a — Directorio poblado
with tempfile.TemporaryDirectory() as tmp:
    tmp_path = Path(tmp)
    for i in range(5):
        (tmp_path / f"file_{i}.txt").write_text("data")
    sub_a = tmp_path / "sub_a"
    sub_a.mkdir()
    (sub_a / "nested.txt").write_text("nested")
    sub_b = tmp_path / "sub_b"
    sub_b.mkdir()
    (sub_b / "another.txt").write_text("more")

    initial_count = len(os.listdir(tmp))
    removed = main_mod._empty_dir_contents(tmp)
    leftover = os.listdir(tmp)

    check(
        "_empty_dir_contents() elimina todos los elementos hijo",
        leftover == [],
        f"inicial={initial_count}, removidos={removed}, restante={leftover}",
    )
    check(
        "_empty_dir_contents() NO elimina el propio directorio",
        os.path.exists(tmp),
        f"path sigue existiendo",
    )

# 3b — Directorio inexistente: debe retornar 0 sin lanzar excepción
mk = os.path.join(tempfile.gettempdir(), "definitely_nonexistent_path_xyz_12345_")
if os.path.exists(mk):
    try:
        os.rmdir(mk)
    except OSError:
        pass
removed_nx = main_mod._empty_dir_contents(mk)
check(
    "_empty_dir_contents() retorna 0 sobre directorio inexistente",
    removed_nx == 0,
    f"retorno: {removed_nx}",
)


# ---------------------------------------------------------------------------
# Test 4: Enrutamiento cross-platform — VERIFICACIÓN DE RUTAS (sin tocar FS)
#
# En lugar de crear archivos reales en subdirectorios como ".Trash" (lo que
# causa problemas en macOS donde el sistema ya gestiona esos nombres), mockeamos
# _empty_dir_contents y verificamos que las funciones DERIVAN las rutas
# correctas para cada SO.
# ---------------------------------------------------------------------------
section("4. Enrutamiento cross-platform (verificación de rutas derivadas)")


def test_os_routing(target_os):
    """Para un SO dado, verifica que se DERIVAN las rutas correctas hacia
    _empty_dir_contents (en macOS) o subprocess (en Windows)."""
    with tempfile.TemporaryDirectory() as safe_tmp:
        safe_path = Path(safe_tmp)
        env = {}
        if target_os == "windows":
            env["TEMP"] = safe_tmp
            env["TMP"] = safe_tmp
            env["LOCALAPPDATA"] = safe_tmp
        elif target_os == "darwin":
            env["TMPDIR"] = safe_tmp
        # Linux: ya no se prueba — soporte descontinuado.

        with patch.dict(os.environ, env, clear=False), \
             patch.object(main_mod.platform, "system", return_value=target_os), \
             patch.object(Path, "home", return_value=safe_path), \
             patch.object(main_mod, "_empty_dir_contents",
                          return_value=99) as mock_empty, \
             patch.object(main_mod, "subprocess") as mock_subp:
            # Permitir que el código use las clases reales como atributos
            mock_subp.TimeoutExpired = _subprocess.TimeoutExpired
            mock_subp.SubprocessError = _subprocess.SubprocessError
            mock_subp.run.return_value = None

            try:
                main_mod.empty_recycle_bin()
                main_mod.clear_temp_files()
                main_mod.clear_system_cache()
            except Exception as e:
                check(f"[{target_os}] sin excepciones", False, f"{type(e).__name__}: {e}")
                return

            # Rutas que se PASARON a _empty_dir_contents (mockeado → no se ejecuta)
            called = [
                str(call.args[0])
                for call in mock_empty.call_args_list
                if call.args
            ]

            if target_os == "windows":
                # Papelera→PowerShell, no _empty_dir_contents.
                ran_powershell = mock_subp.run.called and "powershell" in str(
                    mock_subp.run.call_args
                ).lower()
                check(
                    f"[{target_os}] empty_recycle_bin usa PowerShell Clear-RecycleBin",
                    ran_powershell,
                    str(mock_subp.run.call_args)[:80],
                )
                # clear_temp_files debe llamar _empty_dir_contents con TEMP y TMP.
                n = called.count(safe_tmp)
                check(
                    f"[{target_os}] clear_temp_files usa TEMP/TMP -> _empty_dir_contents",
                    n >= 2,
                    f"safe_tmp llamado {n} veces en {called}",
                )
                # clear_system_cache: LOCALAPPDATA\\Microsoft\\Windows\\INetCache.
                # Estos subdirs no se crean aquí, así que solo se verifica el path.
                check(
                    f"[{target_os}] sin excepciones en las 3 fases de limpieza",
                    True,
                    f"subprocess.run invocado: {mock_subp.run.called}",
                )
            elif target_os == "darwin":
                # ~/.Trash debe estar entre las rutas llamadas.
                trash = str(safe_path / ".Trash")
                check(
                    f"[{target_os}] empty_recycle_bin visita ~/.Trash",
                    trash in called,
                    f"esperaba {trash} en {called}",
                )
                # TMPDIR debe estar entre las rutas llamadas.
                check(
                    f"[{target_os}] clear_temp_files usa TMPDIR",
                    safe_tmp in called,
                    f"esperaba {safe_tmp} en {called}",
                )
            # Linux ya no se prueba aquí: soporte descontinuado.


# Soporte Linux eliminado: sólo se validan Windows y macOS.
for target_os in ("windows", "darwin"):
    test_os_routing(target_os)


# ---------------------------------------------------------------------------
# Test 5: run_full_cleanup respeta stop_flag en cada fase
# ---------------------------------------------------------------------------
section("5. Cancelación cooperativa (stop_flag)")

callbacks_log = []


def log_progress(p):
    callbacks_log.append(("progress", p))


def log_status(s):
    callbacks_log.append(("status", s))


def log_done(success, cancelled=False):
    callbacks_log.append(("done", success, cancelled))


def cancel_immediately(stop_flag=None):
    """Helper que activa el flag y omite la limpieza real."""
    if stop_flag is not None:
        stop_flag.set()
    return None


# Mockeamos todas las funciones de borrado para evitar tocar FS en estos tests.
# (Patrón save/restore: nunca usamos `del` para evitar romper lookup global.)
saved_recycle = main_mod.empty_recycle_bin
saved_temp = main_mod.clear_temp_files
saved_cache = main_mod.clear_system_cache

main_mod.empty_recycle_bin = cancel_immediately
main_mod.clear_temp_files = cancel_immediately
main_mod.clear_system_cache = cancel_immediately

try:
    # Caso A: stop_flag YA seteado al iniciar → debe terminar inmediatamente.
    callbacks_log.clear()
    stop_pre = threading.Event()
    stop_pre.set()
    main_mod.run_full_cleanup(stop_pre, log_status, log_done)
    done_events = [c for c in callbacks_log if c[0] == "done"]
    check(
        "stop_flag pre-seteado aborta run_full_cleanup inmediatamente",
        len(done_events) == 1 and done_events[0] == ("done", False, True),
        f"eventos done: {done_events}",
    )

    # Caso B: flujo normal sin stop_flag y sin cancelaciones → debe completar con éxito.
    # Suspendemos los mocks de cancelación y los reemplazamos por stubs no-op
    # que NO activan el flag, para verificar el camino de completion sin
    # que los helpers triguen la cancelación.
    def no_cancel(stop_flag=None):
        return None
    main_mod.empty_recycle_bin = no_cancel
    main_mod.clear_temp_files = no_cancel
    main_mod.clear_system_cache = no_cancel
    callbacks_log.clear()
    main_mod.run_full_cleanup(None, log_status, log_done)
    done_events = [c for c in callbacks_log if c[0] == "done"]
    check(
        "run_full_cleanup() sin stop_flag completa con éxito",
        len(done_events) == 1 and done_events[0][1] == True,
        f"eventos done: {done_events}",
    )

    # Caso C: flag pre-set cancela ANTES de empty_recycle_bin (cancel en fase 0).
    callbacks_log.clear()
    stop_p0 = threading.Event()
    stop_p0.set()  # Set ANTES de empezar
    main_mod.run_full_cleanup(stop_p0, log_status, log_done)
    done_events = [c for c in callbacks_log if c[0] == "done"]
    check(
        "stop_flag pre-set cancela ANTES de fase 1 (papelera)",
        len(done_events) == 1 and done_events[0] == ("done", False, True),
        f"eventos done: {done_events}",
    )

    # Caso D: mock reciclada que setea el flag en su primera ejecución.
    # run_full_cleanup debe detectar la cancelación y abortar.
    def cancel_after_recycle(stop_flag=None):
        if stop_flag is not None:
            stop_flag.set()
        return None

    main_mod.empty_recycle_bin = cancel_after_recycle
    callbacks_log.clear()
    stop_p1 = threading.Event()
    main_mod.run_full_cleanup(stop_p1, log_status, log_done)
    done_events = [c for c in callbacks_log if c[0] == "done"]
    check(
        "stop_flag.set() durante fase 1 cancela fases siguientes",
        len(done_events) == 1 and done_events[0] == ("done", False, True),
        f"eventos done: {done_events}",
    )

finally:
    # Restaurar las funciones originales (patrón save/restore, nunca del).
    main_mod.empty_recycle_bin = saved_recycle
    main_mod.clear_temp_files = saved_temp
    main_mod.clear_system_cache = saved_cache


# ---------------------------------------------------------------------------
# Test 6: Errores de subprocess NO deben romper la app (Windows)
# ---------------------------------------------------------------------------
section("6. Manejo robusto de subprocess (Windows)")


def test_subprocess_error(side_effect, label):
    fake_mod = MagicMock()
    fake_mod.run.side_effect = side_effect
    fake_mod.TimeoutExpired = _subprocess.TimeoutExpired
    fake_mod.SubprocessError = _subprocess.SubprocessError

    with patch.object(main_mod.platform, "system", return_value="windows"), \
         patch.object(main_mod, "subprocess", fake_mod):
        try:
            main_mod.empty_recycle_bin()
            check(f"empty_recycle_bin() maneja {label}", True)
        except Exception as e:
            check(
                f"empty_recycle_bin() maneja {label}",
                False,
                f"se propagó {type(e).__name__}: {e}",
            )


test_subprocess_error(
    _subprocess.TimeoutExpired("powershell", 30),
    "subprocess.TimeoutExpired",
)
test_subprocess_error(
    FileNotFoundError("powershell no encontrado"),
    "FileNotFoundError (powershell ausente)",
)
test_subprocess_error(
    OSError(13, "Permission denied"),
    "OSError genérico",
)


# ---------------------------------------------------------------------------
# Test 7 eliminado: CleanBoostApp (GUI tkinter) ya no existe.
# La app es terminal-only (CleanBoostCLI). Ver tests 8-10 para ANSI/CLI.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test 8: Helpers ANSI y convención NO_COLOR
# ---------------------------------------------------------------------------
section("8. Helpers ANSI y convención NO_COLOR")

# 8a — TTY sin NO_COLOR: ansi() debe envolver con códigos.
# (Esta vez NO hay que setear ninguna constante global: el helper
# _no_color_enabled() se evalúa dinámicamente.)
saved_stdout = sys.stdout
try:
    sys.stdout = _FakeTTY()
    out = main_mod.ansi("hello", 38, 5, 46)
    check(
        "ansi() envuelve con códigos cuando hay TTY sin NO_COLOR",
        out.startswith("\033[") and "hello" in out and "\033[0m" in out,
        f"salida: {out!r}",
    )
    # 8b — themed('CB', 'green') ahora mapea a 38;5;46 (true bright green / SpringGreen1).
    # Históricamente mapeaba a 38;5;220 ("gold neón"), pero ese código ANSI 220 renderea
    # como amarillo dorado en iTerm2/Terminal.app, lo que confundía al usuario con un acento
    # warning. v3.1.1 migra 'green' a ANSI 46 (True bright green) para coherencia semántica.
    out2 = main_mod.themed("CB", "green")
    check(
        "themed('CB', 'green') incluye 38;5;46 (true bright green)",
        "38;5;46" in out2 and "CB" in out2,
        f"salida: {out2!r}",
    )
finally:
    sys.stdout = saved_stdout

# 8c — NO_COLOR=1: devolver texto plano.
with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False), \
     patch.object(sys, "stdout", _FakeTTY()):
    out = main_mod.ansi("hello", 38, 5, 46)
    check(
        "ansi() devuelve texto plano cuando NO_COLOR está activo",
        out == "hello",
        f"salida: {out!r}",
    )

# 8d — TERM=dumb: también desactiva ANSI.
with patch.dict(os.environ, {"TERM": "dumb"}, clear=False), \
     patch.object(sys, "stdout", _FakeTTY()):
    out = main_mod.ansi("hello", 38, 5, 46)
    check(
        "ansi() devuelve texto plano cuando TERM=dumb",
        out == "hello",
        f"salida: {out!r}",
    )

# 8e — stdout no-TTY (piped): texto plano aunque TERM diga lo contrario.
with patch.object(sys, "stdout", _NonTTY()):
    out = main_mod.ansi("hello", 38, 5, 46)
    check(
        "ansi() devuelve texto plano cuando stdout no es TTY (pipe)",
        out == "hello",
        f"salida: {out!r}",
    )


# ---------------------------------------------------------------------------
# Test 9: run_full_cleanup extendido — kwargs clean_recycle/temp/cache
# ---------------------------------------------------------------------------
section("9. run_full_cleanup: kwargs clean_recycle/temp/cache")

call_log = []


def _setup_phase_mocks():
    """Mockea todas las funciones de limpieza para no tocar FS."""
    return [
        patch.object(main_mod, "empty_recycle_bin",
                     lambda stop_flag=None: call_log.append("recycle")),
        patch.object(main_mod, "clear_temp_files",
                     lambda stop_flag=None: call_log.append("temp")),
        patch.object(main_mod, "clear_system_cache",
                     lambda stop_flag=None: call_log.append("cache")),
        patch.object(main_mod, "optimize_shader_caches",
                     lambda stop_flag=None: call_log.append("shaders")),
        patch.object(main_mod, "optimize_platform",
                     lambda plat, stop_flag=None: call_log.append(f"plat:{plat}")),
    ]


def _noop_status(s):
    pass


def _collect_done(ok, cancelled=False):
    call_log.append(("done", ok, cancelled))


# 9a — defaults: corre recycle+temp+cache+shaders.
call_log.clear()
_patches_a = _setup_phase_mocks()
for p in _patches_a:
    p.start()
try:
    main_mod.run_full_cleanup(None, _noop_status, _collect_done)
finally:
    for p in _patches_a:
        p.stop()
check(
    "defaults llaman recycle+temp+cache+shaders y done(True)",
    all(x in call_log for x in ("recycle", "temp", "cache", "shaders"))
    and any(x == ("done", True, False) for x in call_log),
    f"log: {call_log}",
)

# 9b — clean_recycle=False: omite papelera.
call_log.clear()
_patches_b = _setup_phase_mocks()
for p in _patches_b:
    p.start()
try:
    main_mod.run_full_cleanup(None, _noop_status, _collect_done,
                              clean_recycle=False)
finally:
    for p in _patches_b:
        p.stop()
check(
    "clean_recycle=False omite papelera",
    "recycle" not in call_log and "temp" in call_log,
    f"log: {call_log}",
)

# 9c — clean_temp=False: omite temporales.
call_log.clear()
_patches_c = _setup_phase_mocks()
for p in _patches_c:
    p.start()
try:
    main_mod.run_full_cleanup(None, _noop_status, _collect_done,
                              clean_temp=False)
finally:
    for p in _patches_c:
        p.stop()
check(
    "clean_temp=False omite temporales",
    "temp" not in call_log and "recycle" in call_log,
    f"log: {call_log}",
)

# 9d — clean_cache=False: omite caché de sistema.
call_log.clear()
_patches_d = _setup_phase_mocks()
for p in _patches_d:
    p.start()
try:
    main_mod.run_full_cleanup(None, _noop_status, _collect_done,
                              clean_cache=False)
finally:
    for p in _patches_d:
        p.stop()
check(
    "clean_cache=False omite caché de sistema",
    "cache" not in call_log and "recycle" in call_log,
    f"log: {call_log}",
)

# 9e — todos los flags False + sin plataformas: done(True) sin limpiar nada.
call_log.clear()
_patches_e = _setup_phase_mocks()
for p in _patches_e:
    p.start()
try:
    main_mod.run_full_cleanup(
        None, _noop_status, _collect_done,
        clean_shaders=False,
        clean_recycle=False, clean_temp=False, clean_cache=False,
        selected_platforms=[],
    )
finally:
    for p in _patches_e:
        p.stop()
done_entries = [x for x in call_log if isinstance(x, tuple) and x[0] == "done"]
check(
    "todas las fases desactivadas → done(True, False) sin limpiar nada",
    len(done_entries) == 1 and done_entries[0] == ("done", True, False),
    f"log: {call_log}",
)


# ---------------------------------------------------------------------------
# Test 10: CleanBoostCLI — inicialización y estructura
# ---------------------------------------------------------------------------
section("10. CleanBoostCLI: estructura + inicialización aislada")

fake_specs = {
    "os": "linux",
    "cpu_count": 8,
    "cpu_name": "Fake CPU",
    "ram_gb": 16,
    "disk_free_gb": 100,
    "disk_total_gb": 500,
    "gpu_name": "Fake GPU",
}
fake_games = [
    {"name": "Steam",      "available": True,  "count": 5,  "path": "/fake/steam"},
    {"name": "Epic Games", "available": False, "count": 0,  "path": None},
    {"name": "Minecraft",  "available": True,  "count": 1,  "path": "/fake/.minecraft"},
]

with patch.object(main_mod, "get_system_specs", return_value=fake_specs), \
     patch.object(main_mod, "detect_games", return_value=fake_games), \
     patch.object(sys, "stdout", _FakeTTY()):
    cli = main_mod.CleanBoostCLI()

check(
    "CleanBoostCLI se puede instanciar sin display server",
    cli is not None,
    "obj creado",
)
check(
    "CleanBoostCLI expone specs detectadas",
    cli.specs.get("cpu_name") == "Fake CPU",
    f"cpu_name: {cli.specs.get('cpu_name')}",
)
check(
    "CleanBoostCLI expone games detectados",
    len(cli.games) == 3 and cli.games[0]["name"] == "Steam",
    f"games: {[g['name'] for g in cli.games]}",
)
check(
    "CleanBoostCLI tiene banderas de selección inicializadas",
    all(v is False for v in cli.platform_vars.values())
    and cli.shaders_var is True
    and cli.recycle_var is True
    and cli.temp_var    is True
    and cli.cache_var   is True,
    f"vars iniciales OK",
)
check(
    "main.py expone _no_color_enabled() como función dinámica",
    hasattr(main_mod, "_no_color_enabled") and callable(main_mod._no_color_enabled),
    "función callable para checks runtime",
)

cli_methods_required = [
    "run", "_banner", "_specs_panel", "_games_panel", "_print_menu",
    "_ask", "_ask_yn", "_confirm_and_run", "_run_cleanup",
    "_animate_progress", "_render_bar", "_finish", "_goodbye",
]
missing_cli = [m for m in cli_methods_required if not hasattr(cli, m)]
check(
    "CleanBoostCLI tiene todos los métodos requeridos",
    not missing_cli,
    f"faltantes: {missing_cli}" if missing_cli else "OK",
)

gathered = cli._gather_full_selection()
check(
    "_gather_full_selection devuelve SOLO plataformas disponibles y kwargs",
    isinstance(gathered, dict)
    and set(gathered.keys()) == {
        "selected_platforms", "clean_shaders",
        "clean_recycle", "clean_temp", "clean_cache",
    }
    and gathered["selected_platforms"] == ["Steam", "Minecraft"],
    f"gathered: {gathered}",
)

# Banner es ASCII art blocky de CLEANBOOST. Verificamos que el bloque-art
# está presente reconociendo patrones únicos de la primera fila de varias
# letras (la cadena literal "CLEANBOOST" ya no aparece contigua porque cada
# letra está dibujada con bloques ``█`` separados por espacios).
with patch.object(sys, "stdout", saved_stdout):
    banner = main_mod._CLI_BANNER
    # Patrones únicos de la primera fila para letras con block-arts
    # diferenciables (evitamos A/E/O/T que comparten top-row con otras).
    unique_anchors = (
        " \u2588\u2588\u2588\u2588",  # C  (top: space, 4 blocks) \u2014 5 chars
        "\u2588\u2588\u2588\u2588\u2588",  # E  (top: 5 blocks) \u2014 5 chars, full top bar
        "\u2588  \u2588\u2588",  # N  (bottom diagonal: block + 2 spaces + 2 blocks) \u2014 5 chars
        "\u2588\u2588\u2588\u2588 ",  # B  (top: 4 blocks + space) \u2014 5 chars
    )
    has_block_art = (
        banner.count("\n") >= 4
        and banner.count("█") >= 30
        and all(anchor in banner for anchor in unique_anchors)
    )
    check(
        "_CLI_BANNER es ASCII art blocky multi-línea con 9 letras",
        has_block_art,
        f"newlines={banner.count(chr(10))}, blocks={banner.count('█')}, "
        f"anchors_present={sum(1 for a in unique_anchors if a in banner)}/4",
    )


# ---------------------------------------------------------------------------
# Test 11: main() — dispatch único hacia CleanBoostCLI + rechazo de Linux
# ---------------------------------------------------------------------------
section("11. main() — dispatch y rechazo de Linux")

# linux: debe rechazar amablemente (SystemExit 0) sin invocar CLI/App.
# OJO: como ahora linux también rechaza los flags de daemon, hacemos el
# chequeo para el flujo CLI y para el flujo --enable-daemon en el mismo
# escenario (get_os=linux). Ambos deben SystemExit(0) sin tocar nada.
with patch.object(main_mod, "get_os", return_value="linux"), \
     patch.object(main_mod, "CleanBoostCLI") as cli_cls_mock, \
     patch.object(main_mod, "CleanBoostApp", create=True) as app_cls_mock, \
     patch.object(main_mod, "daemon", create=True) as daemon_mod_mock, \
     redirect_stdout(io.StringIO()), \
     redirect_stderr(io.StringIO()) as err_buf:
    linux_exit_code = "no se lanzó SystemExit"
    try:
        main_mod.main()
    except SystemExit as e:
        linux_exit_code = e.code
    check(
        "main() en linux lanza SystemExit con código 0",
        linux_exit_code == 0,
        f"código: {linux_exit_code!r}",
    )
    check(
        "main() en linux NO llama a CleanBoostCLI",
        not cli_cls_mock.called,
        f"CLI.called={cli_cls_mock.called}",
    )
    check(
        "main() en linux NO llama a CleanBoostApp",
        not app_cls_mock.called,
        f"App.called={app_cls_mock.called}",
    )
    check(
        "main() en linux imprime mensaje informativo de rechazo",
        "Soporte para Linux descontinuado" in err_buf.getvalue(),
        f"stderr: {err_buf.getvalue()!r}",
    )

# windows: debe invocar CleanBoostCLI (y NUNCA a CleanBoostApp).
with patch.object(main_mod, "get_os", return_value="windows"), \
     patch.object(main_mod, "CleanBoostCLI") as cli_cls_mock, \
     patch.object(main_mod, "CleanBoostApp", create=True) as app_cls_mock, \
     redirect_stdout(io.StringIO()), \
     redirect_stderr(io.StringIO()):
    main_mod.main()
    check(
        "main() en windows invoca CleanBoostCLI",
        cli_cls_mock.called,
        f"CLI.called={cli_cls_mock.called}",
    )
    check(
        "main() en windows NUNCA invoca CleanBoostApp",
        not app_cls_mock.called,
        f"App.called={app_cls_mock.called}",
    )

# darwin: mismo comportamiento que windows.
with patch.object(main_mod, "get_os", return_value="darwin"), \
     patch.object(main_mod, "CleanBoostCLI") as cli_cls_mock, \
     patch.object(main_mod, "CleanBoostApp", create=True) as app_cls_mock, \
     redirect_stdout(io.StringIO()), \
     redirect_stderr(io.StringIO()):
    main_mod.main()
    check(
        "main() en darwin invoca CleanBoostCLI",
        cli_cls_mock.called,
        f"CLI.called={cli_cls_mock.called}",
    )
    check(
        "main() en darwin NUNCA invoca CleanBoostApp",
        not app_cls_mock.called,
        f"App.called={app_cls_mock.called}",
    )


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Test 12: i18n — get_locale + t() (detección de locale + traducción)
# ---------------------------------------------------------------------------
section("12. i18n — get_locale + t()")

# 12a — --lang override via CLI gana sobre entorno.
check(
    "get_locale() --lang=en devuelve 'en'",
    main_mod.get_locale(argparse.Namespace(lang='en')) == 'en',
    f"devuelto: {main_mod.get_locale(argparse.Namespace(lang='en'))!r}",
)
check(
    "get_locale() --lang=es devuelve 'es'",
    main_mod.get_locale(argparse.Namespace(lang='es')) == 'es',
    f"devuelto: {main_mod.get_locale(argparse.Namespace(lang='es'))!r}",
)
check(
    "get_locale() --lang=fr (no soportado) → fallback a detección",
    main_mod.get_locale(argparse.Namespace(lang='fr')) in ('en', 'es'),
    f"devuelto: {main_mod.get_locale(argparse.Namespace(lang='fr'))!r}",
)

# 12b — Precedencia de variables de entorno.
saved_env = {k: os.environ.get(k) for k in ('LC_ALL', 'LC_MESSAGES', 'LANG')}
try:
    for var in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        os.environ.pop(var, None)
    os.environ['LANG'] = 'en_US.UTF-8'
    check(
        "get_locale() LANG=en_US.UTF-8 → 'en'",
        main_mod.get_locale(None) == 'en',
        f"devuelto: {main_mod.get_locale(None)!r}",
    )
    os.environ['LC_ALL'] = 'es_ES.UTF-8'
    check(
        "get_locale() LC_ALL=es_ES.UTF-8 → 'es'",
        main_mod.get_locale(None) == 'es',
        f"devuelto: {main_mod.get_locale(None)!r}",
    )
    os.environ['LC_ALL'] = 'es_ES.UTF-8'
    os.environ['LANG'] = 'en_US.UTF-8'
    check(
        "get_locale() LC_ALL gana sobre LANG",
        main_mod.get_locale(None) == 'es',
        f"devuelto: {main_mod.get_locale(None)!r}",
    )
finally:
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

# 12c — t() traduce al idioma activo (round-trip).
main_mod.set_lang('es')
es_str = main_mod.t('header_specs')
check(
    "t('header_specs') en español devuelve cadena ES del dict",
    es_str == main_mod._STRINGS['es']['header_specs'],
    f"devuelto: {es_str!r}",
)
main_mod.set_lang('en')
en_str = main_mod.t('header_specs')
check(
    "t('header_specs') en inglés devuelve cadena EN del dict",
    en_str == main_mod._STRINGS['en']['header_specs'],
    f"devuelto: {en_str!r}",
)
check(
    "t('header_specs') ES != EN (las traducciones difieren)",
    es_str != en_str,
    f"ES={es_str!r} EN={en_str!r}",
)

# 12d — t() interpola kwargs correctamente.
check(
    "t('health_disk_low', pct=42) interpola {pct}",
    '42' in main_mod.t('health_disk_low', pct=42),
    f"devuelto: {main_mod.t('health_disk_low', pct=42)!r}",
)
check(
    "t('msg_success', m=3, s=14) interpola tiempo",
    '03:14' in main_mod.t('msg_success', m=3, s=14),
    f"devuelto: {main_mod.t('msg_success', m=3, s=14)!r}",
)
check(
    "t('msg_fail_error', m=1, s=5) tiene X:XX",
    '01:05' in main_mod.t('msg_fail_error', m=1, s=5),
    f"devuelto: {main_mod.t('msg_fail_error', m=1, s=5)!r}",
)

# 12e — Fallback a EN si la key no existe en el idioma activo.
saved_header_es = main_mod._STRINGS['es'].pop('header_specs', None)
main_mod.set_lang('es')
check(
    "t() con key faltante en ES → fallback a EN",
    main_mod.t('header_specs') == main_mod._STRINGS['en']['header_specs'],
    f"devuelto: {main_mod.t('header_specs')!r}",
)
if saved_header_es is not None:
    main_mod._STRINGS['es']['header_specs'] = saved_header_es

# 12f — Último fallback: la key literal si tampoco existe en EN (defensa typos).
main_mod._CURRENT_LANG = 'xx'
check(
    "t() con idioma inválido y key inexistente → devuelve literal",
    main_mod.t('zzz_nonexistent_key_xyz') == 'zzz_nonexistent_key_xyz',
    f"devuelto: {main_mod.t('zzz_nonexistent_key_xyz')!r}",
)
main_mod._CURRENT_LANG = 'en'

# 12h — _STRINGS tiene buckets 'en' y 'es' completas.
check(
    "_STRINGS tiene buckets 'en' y 'es'",
    set(main_mod._STRINGS.keys()) >= {'en', 'es'},
    f"keys: {sorted(main_mod._STRINGS.keys())}",
)
check(
    "_STRINGS['en']['header_specs'] contiene 'SPECIFICATIONS'",
    'SPECIFICATIONS' in main_mod._STRINGS['en']['header_specs'],
    f"EN: {main_mod._STRINGS['en']['header_specs']!r}",
)
check(
    "_STRINGS['es']['header_specs'] contiene 'TUS ESPECIFICACIONES'",
    'TUS ESPECIFICACIONES' in main_mod._STRINGS['es']['header_specs'],
    f"ES: {main_mod._STRINGS['es']['header_specs']!r}",
)
# Resumen
# ---------------------------------------------------------------------------
section("RESUMEN")
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed
print(f"  Total:   {total}")
print(f"  Pasados: {passed}")
print(f"  Fallados: {failed}")
print()

if failed == 0:
    print("  ✓ TODOS LOS TESTS PASARON — la lógica de CLEANBOOST está sana.")
    print()
    print("  Nota: CleanBoost ahora es terminal-only (sin GUI). Para")
    print("  probarlo manualmente, ejecuta:")
    print()
    print("      python3 main.py")
    sys.exit(0)
else:
    print("  ✗ Algunos tests fallaron. Revisa arriba los detalles.")
    sys.exit(1)
