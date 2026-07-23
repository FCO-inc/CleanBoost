# CleanBoost v3.1.1 — Cyberpunk System & Gaming Optimizer

Optimizador de cachés para Windows y macOS. **Solo terminal.** Sin GUI.
Sin dependencias externas. Sin telemetría. Sin hosting.

## ¿Qué hace?

- Vacía la papelera de reciclaje (Windows) o `.Trash` (macOS).
- Borra archivos temporales del usuario.
- Vacía cachés del sistema (Microsoft INetCache / macOS `Library/Caches`).
- Limpia cachés de shaders (DirectX, NVIDIA, AMD en Windows; Steam en macOS).
- Optimiza las cachés de tus bibliotecas de juegos: **Steam, Epic Games,
  Battle.net, GOG Galaxy, Minecraft, Roblox** (todas instaladas legítimamente).

## Requisitos

- **Python 3.8+** en PATH.
- **CERO dependencias externas** (solo biblioteca estándar).
- Windows 10+ (1809+) o macOS 10.13+ (Alta Sierra).
- **Linux no soportado** — las distribuciones Linux ya gestionan cachés,
  temporales y papelera de forma nativa, por lo que CleanBoost emite un
  mensaje informativo y termina (código 0) si se invoca allí.

## Instalación

### Vía `pip` (recomendada)

```bash
python3 -m pip install --user cleanboost
cleanboost --version     # → cleanboost 3.1.1
cleanboost               # menú interactivo 3 botones
cleanboost --quick       # ejecuta AMBAS sin prompts (cron-friendly)
cleanboost --lang=en|es  # fuerza idioma independientemente del locale
```

> El paquete PyPI se llama `cleenboost` (identidad legacy preservada para
> que `pip install --upgrade cleenboost` siga funcionando en instalaciones
> existentes). El binario entry-point y el nombre del comando siguen siendo
> `cleanboost` por convención PEP 621 (lowercase).

> Si tu shell no tiene `~/.local/bin` en PATH, añade antes
> `export PATH="$HOME/.local/bin:$PATH"` a `~/.zshrc` o `~/.bashrc`.

### Vía `npm` (macOS / Windows single-binary)

```bash
npm install -g cleenboost
```

> El paquete npm también se publica como `cleenboost` (legacy). El binario
> se descarga de los GitHub Releases y se extrae a `~/.cleanboost/bin/`.

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
└── npm-cli/             ← wrapper npm que descarga el prebuilt binario
```

## Licencia

MIT — ver [`LICENSE`](LICENSE).

Úsalo, modifícalo, distribúyelo. PRs bienvenidos contra
[github.com/Freebuff/cleanboost](https://github.com/Freebuff/cleanboost).
