# CleanBoost v3.1.1 — Cyberpunk System & Gaming Optimizer

Optimizador de cachés para Windows y macOS. **Solo terminal.** Sin GUI.
Sin dependencias externas. Sin telemetría. Sin hosting. **100% local.**
**No es un virus** — es código abierto MIT, auditable, ~2000 líneas de
Python puro.

## ¿Qué hace?

- Vacía la papelera de reciclaje (Windows) o `.Trash` (macOS).
- Borra archivos temporales del usuario.
- Vacía cachés del sistema (Microsoft INetCache / macOS `Library/Caches`).
- Limpia cachés de shaders (DirectX, NVIDIA, AMD en Windows; Steam en macOS).
- Optimiza las cachés de tus bibliotecas de juegos: **Steam, Epic Games,
  Battle.net, GOG Galaxy, Minecraft, Roblox** (todas instaladas legítimamente).

> **Resumen en una línea:** libera espacio en disco borrando de forma
> Segura sólo archivos que el sistema o el propio juego va a regenerar
> solos. **No toca** tus documentos, fotos, descargas, ni nada que no sea
> regenerable.

## 🛡️ Trust & Privacy — No es un virus

- **Código abierto MIT.** Cada línea auditable en
  [github.com/Freebuff/cleanboost](https://github.com/Freebuff/cleanboost).
  ~2 000 líneas de Python puro + scripts bash/batch + paquete npm de
  ~150 líneas. Sin minificadores, sin ofuscación.
- **Cero dependencias externas.** Sólo la biblioteca estándar de Python
  (`os`, `shutil`, `subprocess`, `pathlib`, `argparse`, `threading`).
  Nada de requests, nada de urllib en runtime, nada de CryptoPP, nada de
  PyYAML dinámico. Verificable con `pip show cleenboost` (el campo
  `Requires` debe estar vacío y la lista de archivos sólo apunta a
  módulos stdlib).
- **100% local, 100% offline.** Tras `pip install` o equivalente,
  CleanBoost **no hace ninguna llamada de red**. Cero. Ni telemetría, ni
  analytics, ni crash reports, ni update checks, ni phoning home. Ver:
  [`grep -rn 'http\|https\|socket\|urllib\|requests' --include='*.py' main.py daemon.py`](https://github.com/Freebuff/cleanboost).
- **No se inicia solo.** El daemon semanal (`--enable-daemon`) es **opt-in
  explícito**: si no lo activas, no crea ningún fichero en tu sistema.
  Verificable: tras `pip install`, ejecuta
  `ls ~/Library/LaunchAgents/com.user.cleanboost.plist` — no debe
  existir hasta que tú escribas `cleanboost --enable-daemon`.
- **No toca tu sistema sin pedirlo.** Cada fase (papelera, temporales,
  caché sistema, caché shaders, bibliotecas de juego) pregunta `[Y/n]`
  antes de borrar, salvo si ejecutas `--quick` (que sólo borra los
  regenerables: papelera + temporales + cachés del sistema + cachés de
  shaders). Las eliminaciones son reversibles porque los targets son
  regenerables.
- **Sin AV false positives.** El binario single-file PyInstaller a veces
  dispara heurísticas genéricas de antivirus (común a cualquier binario
  generado por PyInstaller en Windows). Para verificar: el código fuente
  está en GitHub y `python -m pip install --user cleenboost` desde PyPI
  instala siempre el wheel firmado originado en el tag `v3.1.1`.
- **Compra/uso seguro.** No requiere permisos elevados. La papelera de
  Windows se vacía con `Clear-RecycleBin -Force` (estándar). La papelera
  de macOS se vacía borrando el contenido de `~/.Trash` (estándar). Nada
  se ejecuta fuera de los directorios listados en este README.

> **TL;DR para Windows SmartScreen y macOS Gatekeeper:** si te aparece
> warning, es porque el binario no está firmado con certificado de
> desarrollador ($400/año). Soluciones: `pip install` desde PyPI (que
> sí usa la cadena de confianza), o "Open anyway" desde Preferencias del
> Sistema.

## 📋 Requisitos

- **Python 3.8+** en PATH.
- **CERO dependencias externas** (solo biblioteca estándar).
- Windows 10+ (1809+) o macOS 10.13+ (Alta Sierra).
- **Linux no soportado** — las distribuciones Linux ya gestionan cachés,
  temporales y papelera de forma nativa, por lo que CleanBoost emite un
  mensaje informativo y termina (código 0) si se invoca allí.

## 🧰 Instalación paso a paso

### Vía `pip` (recomendada)

```bash
python3 -m pip install --user cleenboost    # paquete PyPI = cleenboost
cleanboost --version                        # → cleanboost 3.1.1
cleanboost                                  # menú interactivo 3 botones
cleanboost --quick                          # ejecuta AMBAS sin prompts (cron-friendly)
cleanboost --lang=en|es                     # fuerza idioma independientemente del locale
```

> El **paquete PyPI** se llama `cleenboost` (identidad legacy preservada para
> que `pip install --upgrade cleenboost` siga funcionando en instalaciones
> existentes). El **binario entry-point** y el **comando** que el usuario
> ejecuta son `cleanboost` por convención PEP 621 (lowercase). Tras
> `pip install`, `which cleanboost` debe resolver
> `~/​.local/bin/cleanboost` (macOS/Linux) o
> `%AppData%\Roaming\Python\Python3X\Scripts\cleanboost.exe` (Windows).

> Si tu shell no tiene `~/.local/bin` en PATH, añade antes
> `export PATH="$HOME/.local/bin:$PATH"` a `~/.zshrc` o `~/.bashrc`.

### Vía `npm` (macOS / Windows single-binary)

```bash
# Opción recomendada (nombre de marca):
npm install -g cleanboost

# Equivalente legacy (mismo resultado, mismo binario en PATH):
npm install -g cleenboost
```

> Hay un **paquete stub** llamado `cleanboost` en el registry que tiene
> a `cleenboost` como dependencia runtime: cuando ejecutas `npm install -g
> cleanboost`, npm descarga el stub, instala `cleenboost@3.1.1` anidado,
> y crea los symlinks `cleanboost` / `cleanboost-cli` / `cb` en tu
> `<prefix>/bin`. El binario real se descarga de los GitHub Releases y
> se extrae a `~/.cleanboost/bin/` por el postinstall de `cleenboost`.
>
> Si tienes `cleenboost` ya instalado globalmente y luego ejecutas
> `npm install -g cleanboost`, el symlink de la papelera global se
> sobreescribe con el del stub (que forward-execa al real `cleenboost`) —
> el comportamiento para el usuario es idéntico.

### Vía Homebrew (macOS)

```bash
brew install Freebuff/cleenboost/cleenboost
```

> El tap se llama `homebrew-cleenboost` y el formula también `cleenboost` por
> razones de backward compat. Ver [`packaging/homebrew/README.md`](packaging/homebrew/README.md).

### Vía winget (Windows)

```powershell
winget install --id Freebuff.Cleenboost
```

Ver [`packaging/winget/README.md`](packaging/winget/README.md).

### Doble-click (sin instalar nada)

macOS:

```bash
cp scripts/cleanboost.command ~/Desktop/
chmod +x ~/Desktop/cleanboost.command
```

Windows (PowerShell):

```powershell
Copy-Item scripts\cleanboost.bat $env:USERPROFILE\Desktop\
```

## 📦 Installation (English)

CleanBoost installs as a single binary, requires no runtime
dependencies, and runs entirely in the terminal. It is **100% local**:
no telemetry, no analytics, no remote calls after install.

### Prerequisites

- **Windows 10+** (1809 or later) **or** **macOS 10.13+** (High Sierra).
- **Python 3.8+** on `PATH` for the `pip` channel.
- **Node.js 18+** for the `npm` channel (used only by the postinstall).
- Linux is not supported — the binary prints a friendly notice and exits
  with code 0 if installed there.

### Pick an install channel

#### Step 1 — `pip` (recommended for Python developers)

```bash
python3 -m pip install --user cleenboost
```

The package on PyPI is published as `cleenboost`. The CLI binary and
the `cleanboost`, `cleanboost-cli`, `cb` entry-points are registered
under PEP 621 (lowercase, matching the brand).

#### Step 2 — `npm` (single binary; macOS or Windows)

```bash
# Prefer the brand-canonical name:
npm install -g cleanboost

# Legacy package name (equivalent; both produce the same binary):
npm install -g cleenboost
```

The brand-canonical `cleanboost` package on npm is a thin alias that
depends on the real `cleenboost@3.1.1` package. Either install command
ends with the `cleanboost` binary on your PATH and the prebuilt Python
binary downloaded to `~/.cleanboost/bin/` by `cleenboost`'s postinstall.

#### Step 3 — Homebrew (macOS)

```bash
brew install Freebuff/cleenboost/cleenboost
```

The Homebrew tap is `Freebuff/homebrew-cleenboost`. The formula is
`cleenboost.rb` (class `Cleenboost`). The installed Cellar binary is
symlinked into your `brew --prefix` bin and resolves as `cleanboost`.

#### Step 4 — `winget` (Windows)

```powershell
winget install --id Freebuff.Cleenboost
```

The package identifier `Freebuff.Cleenboost` is fixed across all
manifest versions; upgrades are keyed by it. The display name is
`CleanBoost` and the install moniker is `cleenboost`. The executable
registered with Windows is `cleanboost`.

#### Step 5 — Double-click wrapper (no installer)

macOS:

```bash
cp scripts/cleanboost.command ~/Desktop/
chmod +x ~/Desktop/cleanboost.command
```

Windows (PowerShell):

```powershell
Copy-Item scripts\cleanboost.bat $env:USERPROFILE\Desktop\
```

These resolve `cleanboost` from `PATH` or fall back to running
`python3 main.py` next to the wrapper — useful when no global install
is available.

### Verify the install

```bash
cleanboost --version    # → cleanboost 3.1.1
cleanboost --help       # lists every flag: --quick, --lang, --enable-daemon, ...
cleanboost              # launches the interactive 3-button menu
```

### Quick silent run

```bash
cleanboost --quick
```

Runs the full "BOTH" profile (recycle bin + temp files + system cache
+ shader caches) **without** interactive prompts. Recommended for
cron jobs, launchd, Task Scheduler, and CI.

### Optional weekly reminder (opt-in)

```bash
cleanboost --enable-daemon       # macOS launchd / Windows Task Scheduler
cleanboost --daemon-status       # show current state
cleanboost --disable-daemon      # remove the scheduled task
```

The daemon never installs itself: nothing is written to your system
until you run `--enable-daemon` for the first time.

## Daemon semanal — opt-in

CleanBoost puede correr `--quick` cada domingo a las 10:00 localmente.
**NO** es auto-arranque invasivo: el usuario lo activa explícitamente y
lo puede desactivar en cualquier momento.

```bash
cleanboost --enable-daemon       # crea el servicio (launchd/systemd/Task)
cleanboost --daemon-status       # describe el estado actual
cleanboost --disable-daemon      # elimina el servicio
```

Implementación por SO:
- **macOS** — `launchd` (`~/Library/LaunchAgents/com.user.cleanboost.plist`)
- **Linux** — `systemd` `--user` (soporte removido del flujo principal pero
  `daemon.py` aún maneja los argumentos de systemd si el usuario lo invoca
  manualmente)
- **Windows** — Task Scheduler (XML exportado a `cleanboost.xml`)

## Compatibilidad

- **macOS 10.13+** (Alta Sierra) — Intel x86_64 y Apple Silicon arm64
  (universal2 .tar.gz).
- **Windows 10+** (1809+) — x86_64 y arm64 (con emulación Prism).
- **Python 3.8+** (probado en 3.8, 3.10, 3.12, 3.13).

## Línea ética

CleanBoost optimiza cachés de juegos **legítimamente instalados**. NO se
distribuye soporte para launchers pirateados (warez: FitGirl, DODI, Codex,
etc.). Esta línea no es una feature diferida: es una **renuncia explícita**.
Se aplica sin excepciones.

## Estructura del repo

```
CleanBoost/
├── README.md            ← este archivo
├── LICENSE              ← MIT
├── pyproject.toml       ← `name = "cleenboost"` (PyPI), entrypoints `cleanboost`
├── MANIFEST.in          ← qué entra al sdist
├── main.py              ← CLI banners, i18n ES/EN, 3 botones (OPTIMIZE | CLEAN | BOTH)
├── daemon.py            ← opt-in weekly reminder (launchd/systemd/Task)
├── scripts/             ← wrappers de doble-clic (mac/win/linux desktop)
├── tests/               ← unit tests con tempfile + unittest.mock
├── packaging/
│   ├── build_dmg.sh     ← macOS .app + .dmg (universal2)
│   ├── build_windows.bat ← Windows .exe + .zip
│   ├── make_icon.py     ← genera los .ico/.icns
│   ├── homebrew/        ← formula `cleenboost.rb` + tap README
│   └── winget/          ← manifests `Freebuff.Cleenboost` (PackageIdentifier)
├── npm-cli/             ← paquete npm real `cleenboost` (descarga el prebuilt)
└── npm-cleanboost-stub/ ← paquete npm alias `cleanboost` (depende de cleenboost)
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).

Úsalo, modifícalo, distribúyelo. PRs bienvenidos contra
[github.com/Freebuff/cleanboost](https://github.com/Freebuff/cleanboost).
