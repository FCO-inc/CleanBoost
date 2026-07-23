"""
cleanboost.daemon — Aviso periódico semanal (opt-in).

Sistema soportado:
    * macOS  : launchd  ~/Library/LaunchAgents/com.user.cleanboost.plist
    * Linux  : systemd  ~/.config/systemd/user/cleanboost.service (+ timer)
    * Windows: Task Scheduler (XML exportado a ``cleanboost.xml``)

Por qué opt-in:
    El sistema NO es invasivo. Sin ``--enable-daemon`` no se crea ningún
    fichero en el sistema. Una vez habilitado, el usuario puede desinstalar
    con ``--disable-daemon`` en cualquier momento.

Por qué semanal:
    Cachés de Steam/Epic/Roblox no crecen tanto entre días. Un aviso/semana
    evita spam y consumo extra de CPU/disco en background.

Fallback de permisos:
    ``enable()`` puede fallar por permisos (Full Disk Access en macOS,
    ``os.access`` denegado, falta de política de usuario en Windows). En
    ese caso: log en ``~/.cleanboost/daemon_error.log`` y mensaje amable
    en stdout. NO entra en pánico, NO aborta el proceso principal del CLI.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

USER_DIR = Path.home()
LAUNCH_DIR_MAC = USER_DIR / "Library" / "LaunchAgents"
SYSTEMD_DIR_LINUX = USER_DIR / ".config" / "systemd" / "user"
CLEANBOOST_HOME = USER_DIR / ".cleanboost"
ERROR_LOG = CLEANBOOST_HOME / "daemon_error.log"

LAUNCH_LABEL = "com.user.cleanboost"
SYSTEMD_UNIT = "cleanboost.service"
SYSTEMD_TIMER = "cleanboost.timer"
WIN_TASK_NAME = "CleanBoost Weekly"


def _log_error(msg: str) -> None:
    """Log silencioso a disco cuando algo va mal durante install/uninstall.
    No imprime a stdout: ya lo hace la respuesta amable al usuario.
    """
    try:
        CLEANBOOST_HOME.mkdir(parents=True, exist_ok=True)
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{__import__('datetime').datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except OSError:
        # Si no podemos escribir siquiera al log, no hay nada que hacer.
        pass


def _python_executable() -> str:
    """Ruta al ejecutable Python que el daemon debe invocar. Preferimos
    ``sys.executable`` del proceso actual: si el usuario corre con un
    venv específico, el daemon respetará ese intérprete."""
    return sys.executable or "python3"


def _script_target_args() -> list[str]:
    """Devuelve la línea de comando que el daemon debe ejecutar, en forma
    lista-de-args (no string). Esto evita problemas con paths que contienen
    espacios: hacer ``prog, _, rest = target.partition(" ")`` rompe cuando
    el install path tiene espacios (p.ej. ``C:\\Program Files\\...``).
    Prioridad:
      1. Entrypoint ``cleanboost`` en PATH (instalación via pip).
      2. ``main.py`` junto al paquete (modo desarrollo / ejecución directa).
    """
    on_path = shutil.which("cleanboost")
    if on_path:
        # ``shutil.which`` con ``pathext`` en Windows ya devuelve el binario
        # con extensión correcta (.exe), pero conservamos el args como lista
        # para que el caller pueda concatenar ``['--quick']`` sin ambigüedad.
        return [on_path]
    here = Path(__file__).resolve().parent
    for candidate in (here / "main.py", here.parent / "main.py"):
        if candidate.exists():
            return [_python_executable(), str(candidate)]
    # Último recurso: asume que el usuario invocará por PATH tras instalar.
    return ["cleanboost"]


def _next_sunday_10am() -> str:
    """Calcula el próximo domingo a las 10:00 en formato ISO local que
    tanto launchd como Task Scheduler aceptan. Solo se llama una vez por
    enable(), por lo que el coste es despreciable.
    """
    import datetime as _dt
    now = _dt.datetime.now()
    # weekday(): lunes=0, domingo=6. Si hoy es domingo y hora>=10,
    # entonces ya disparó hoy; saltamos al siguiente.
    days_ahead = (6 - now.weekday()) % 7
    if days_ahead == 0 and now.hour >= 10:
        days_ahead = 7
    target_date = now.date() + _dt.timedelta(days=days_ahead)
    return f"{target_date.isoformat()}T10:00:00"


# ============================================================================
# macOS — launchd
# ============================================================================
def _macos_enable() -> tuple[bool, str]:
    LAUNCH_DIR_MAC.mkdir(parents=True, exist_ok=True)
    # Asegurar el directorio de logs ANTES de escribir el plist (launchd
    # intenta abrirlo en cuanto carga el agente).
    CLEANBOOST_HOME.mkdir(parents=True, exist_ok=True)
    plist_path = LAUNCH_DIR_MAC / f"{LAUNCH_LABEL}.plist"
    args = _script_target_args() + ["--quick"]
    plist = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        '<dict>\n'
        f'  <key>Label</key><string>{LAUNCH_LABEL}</string>\n'
        f'  <key>ProgramArguments</key>\n'
        '  <array>\n'
        + "".join(f"    <string>{a}</string>\n" for a in args)
        + '  </array>\n'
        '  <key>StartCalendarInterval</key>\n'
        '  <dict>\n'
        '    <key>Weekday</key><integer>0</integer>\n'   # domingo
        '    <key>Hour</key><integer>10</integer>\n'    # 10:00 local
        '  </dict>\n'
        '  <key>RunAtLoad</key><false/>\n'
        '  <key>StandardOutPath</key><string>'
        f'{CLEANBOOST_HOME}/daemon.out.log</string>\n'
        '  <key>StandardErrorPath</key><string>'
        f'{CLEANBOOST_HOME}/daemon.err.log</string>\n'
        '</dict>\n'
        '</plist>\n'
    )
    try:
        plist_path.write_text(plist, encoding="utf-8")
        # Cargar el agent (silencioso si ya existe → unload + load).
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True, check=False,
        )
        r = subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True, timeout=10, check=False,
        )
        if r.returncode != 0:
            _log_error(f"launchctl load failed: {r.stderr.decode(errors='replace')}")
            return False, "launchctl rechazó cargar el agente"
        return True, f"Agente instalado en {plist_path}"
    except (OSError, subprocess.SubprocessError) as e:
        _log_error(f"macOS enable exception: {e}")
        return False, f"No pude escribir/cargar el agente: {e}"


def _macos_disable() -> tuple[bool, str]:
    plist_path = LAUNCH_DIR_MAC / f"{LAUNCH_LABEL}.plist"
    if plist_path.exists():
        subprocess.run(
            ["launchctl", "unload", str(plist_path)],
            capture_output=True, check=False,
        )
        plist_path.unlink()
    return True, "Agente launchd desinstalado"


def _macos_status() -> tuple[bool, str]:
    plist_path = LAUNCH_DIR_MAC / f"{LAUNCH_LABEL}.plist"
    if not plist_path.exists():
        return False, f"Agente NO instalado (esperado en {plist_path})"
    r = subprocess.run(
        ["launchctl", "list", LAUNCH_LABEL],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if r.returncode == 0 and "PID" in r.stdout:
        return True, f"Agente CARGADO. {r.stdout.strip()}"
    return True, f"Agente instalado pero no cargado: {r.stdout.strip() or r.stderr.strip()}"


# ============================================================================
# Linux — systemd (user level)
# ============================================================================
def _linux_enable() -> tuple[bool, str]:
    SYSTEMD_DIR_LINUX.mkdir(parents=True, exist_ok=True)
    CLEANBOOST_HOME.mkdir(parents=True, exist_ok=True)
    service_path = SYSTEMD_DIR_LINUX / SYSTEMD_UNIT
    timer_path = SYSTEMD_DIR_LINUX / SYSTEMD_TIMER
    # Usamos el formato lista-de-args → string con quoting. ``ExecStart``
    # admite múltiples args separados por espacios; shellescape no es
    # necesario porque los paths sólo pueden contener `'\\'` en Windows y
    # `\\` no es un caracter especial para systemd.
    exec_line = " ".join(_script_target_args() + ["--quick"])
    service = (
        "[Unit]\n"
        "Description=CleanBoost weekly cache optimization\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        f"ExecStart={exec_line}\n"
        f"StandardOutput=append:{CLEANBOOST_HOME}/daemon.out.log\n"
        f"StandardError=append:{CLEANBOOST_HOME}/daemon.err.log\n"
    )
    timer = (
        "[Unit]\n"
        "Description=CleanBoost weekly schedule\n\n"
        "[Timer]\n"
        "OnCalendar=Sun 10:00\n"
        "Persistent=true\n\n"
        "[Install]\n"
        "WantedBy=timers.target\n"
    )
    try:
        service_path.write_text(service, encoding="utf-8")
        timer_path.write_text(timer, encoding="utf-8")
        # Intentar recargar + activar. Si falla (ej. sin systemctl), avisar
        # amable: el usuario puede hacerlo manualmente.
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            capture_output=True, timeout=10, check=False,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", SYSTEMD_TIMER],
            capture_output=True, timeout=10, check=False,
        )
        return True, f"Servicio instalado en {service_path}\nTimer instalado en {timer_path}"
    except (OSError, subprocess.SubprocessError) as e:
        _log_error(f"Linux enable exception: {e}")
        return False, f"No pude escribir los unit files: {e}"


def _linux_disable() -> tuple[bool, str]:
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", SYSTEMD_TIMER],
        capture_output=True, check=False,
    )
    for path in (SYSTEMD_DIR_LINUX / SYSTEMD_UNIT,
                 SYSTEMD_DIR_LINUX / SYSTEMD_TIMER):
        if path.exists():
            path.unlink()
    return True, "Servicio systemd desinstalado"


def _linux_status() -> tuple[bool, str]:
    p = SYSTEMD_DIR_LINUX / SYSTEMD_TIMER
    if not p.exists():
        return False, f"Timer NO instalado (esperado en {p})"
    r = subprocess.run(
        ["systemctl", "--user", "is-active", SYSTEMD_TIMER],
        capture_output=True, text=True, timeout=5, check=False,
    )
    return True, f"Unit instalado. Estado systemctl: {r.stdout.strip() or r.stderr.strip()}"


# ============================================================================
# Windows — Task Scheduler (XML portable)
# ============================================================================
def _win_enable() -> tuple[bool, str]:
    CLEANBOOST_HOME.mkdir(parents=True, exist_ok=True)
    xml_path = CLEANBOOST_HOME / "cleanboost.taskscheduler.xml"
    args_list = _script_target_args() + ["--quick"]
    # Task Scheduler XML separa Command (primer arg) y Arguments (resto).
    # Decodificamos entidades XML para que paths con espacios y caracteres
    # especiales (&, <, >) no rompan el parser.
    def _esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace("\"", "&quot;")
        )
    command = _esc(args_list[0])
    arguments = _esc(" ".join(args_list[1:])) if len(args_list) > 1 else "--quick"
    start_boundary = _next_sunday_10am()  # dinámico: evita que esté en el pasado
    xml = (
        '<?xml version="1.0" encoding="UTF-16"?>\n'
        '<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">\n'
        '  <Triggers>\n'
        '    <CalendarTrigger>\n'
        f'      <StartBoundary>{start_boundary}</StartBoundary>\n'
        '      <Enabled>true</Enabled>\n'
        '      <ScheduleByWeek>\n'
        '        <DaysOfWeek><Sunday /></DaysOfWeek>\n'
        '        <WeeksInterval>1</WeeksInterval>\n'
        '      </ScheduleByWeek>\n'
        '    </CalendarTrigger>\n'
        '  </Triggers>\n'
        '  <Actions Context="Author">\n'
        '    <Exec>\n'
        f'      <Command>{command}</Command>\n'
        f'      <Arguments>{arguments}</Arguments>\n'
        '    </Exec>\n'
        '  </Actions>\n'
        '  <Settings>\n'
        '    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>\n'
        '    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>\n'
        '  </Settings>\n'
        '</Task>\n'
    )
    try:
        xml_path.write_text(xml, encoding="utf-16")
        # Importar la tarea vía schtasks.
        r = subprocess.run(
            ["schtasks", "/create", "/tn", WIN_TASK_NAME,
             "/xml", str(xml_path)],
            capture_output=True, timeout=15, check=False,
        )
        if r.returncode != 0:
            _log_error(
                "schtasks failed: " + r.stderr.decode(errors="replace")
            )
            return False, (
                "XML escrito pero no pude registrarlo automáticamente.\n"
                f"  • Software: {xml_path}\n"
                "  • Solución: ejecuta como admin "
                "`schtasks /create /tn CleanBoost /xml "
                f"{xml_path}`\n"
                f"  • Detalle: {r.stderr.decode(errors='replace').strip()}"
            )
        return True, f"Tarea programada creada: {WIN_TASK_NAME}"
    except (OSError, subprocess.SubprocessError) as e:
        _log_error(f"Windows enable exception: {e}")
        return False, f"No pude crear la tarea: {e}"


def _win_disable() -> tuple[bool, str]:
    r = subprocess.run(
        ["schtasks", "/delete", "/tn", WIN_TASK_NAME, "/f"],
        capture_output=True, check=False,
    )
    xml_path = CLEANBOOST_HOME / "cleanboost.taskscheduler.xml"
    if xml_path.exists():
        xml_path.unlink()
    if r.returncode == 0:
        return True, "Tarea programada eliminada"
    return False, "Tarea no estaba registrada (limpio)"


def _win_status() -> tuple[bool, str]:
    r = subprocess.run(
        ["schtasks", "/query", "/tn", WIN_TASK_NAME],
        capture_output=True, text=True, timeout=5, check=False,
    )
    if r.returncode == 0:
        return True, f"Tarea programada: {WIN_TASK_NAME} (activa)"
    return False, f"Tarea NO registrada ({WIN_TASK_NAME})"


# ============================================================================
# Dispatcher
# ============================================================================
def run(*, enable: bool, disable: bool, status: bool) -> None:
    """Punto de entrada invocado desde ``main.py`` cuando el usuario pasa
    ``--enable-daemon`` / ``--disable-daemon`` / ``--daemon-status``."""
    if enable:
        ok, msg = _dispatch("_enable")()
        print(("  ✓ " if ok else "  ⚠ ") + msg)
        if not ok:
            print("  Si el problema persiste, ejecuta el daemon manualmente.")
        return
    if disable:
        ok, msg = _dispatch("_disable")()
        print("  ✓ " + msg)
        return
    if status:
        active, msg = _dispatch("_status")()
        prefix = "  ● " if active else "  ○ "
        print(prefix + msg)


def _dispatch(action: str):
    """Resuelve la implementación según el SO. ``action`` ∈ {'_enable',
    '_disable', '_status'}. Usamos ``getattr`` sobre el módulo actual para
    mantener todo en una sola pasada."""
    os_name = platform.system().lower()
    if os_name.startswith("win"):
        impl = {
            "_enable":  _win_enable,
            "_disable": _win_disable,
            "_status":  _win_status,
        }[action]
        return impl
    if os_name == "darwin":
        impl = {
            "_enable":  _macos_enable,
            "_disable": _macos_disable,
            "_status":  _macos_status,
        }[action]
        return impl
    # Linux u otros POSIX: la app aborta en main() antes de llegar aquí,
    # pero si alguien REPL-llama `daemon.run(...)`, usamos systemd.
    impl = {
        "_enable":  _linux_enable,
        "_disable": _linux_disable,
        "_status":  _linux_status,
    }[action]
    return impl


if __name__ == "__main__":
    # Permite ``python daemon.py --enable-daemon`` para debugging directo.
    main_module = sys.modules.get("__main__")
    argv = sys.argv[1:]
    run(
        enable="--enable-daemon" in argv,
        disable="--disable-daemon" in argv,
        status="--daemon-status" in argv,
    )
