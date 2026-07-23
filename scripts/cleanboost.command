#!/usr/bin/env bash
# cleanboost.command — wrapper de doble-clic para macOS.
# Doble-clic desde Finder abre Terminal con el menú 3 botones de CleanBoost.
# Si el usuario quiere comportamiento silencioso, edite a "cleanboost --quick".

set -e
# Resolución de ``cleanboost`` en PATH vs fallback a ``python3 main.py``.
if command -v cleanboost >/dev/null 2>&1; then
    exec cleanboost
else
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -f "$SCRIPT_DIR/main.py" ]; then
        exec python3 "$SCRIPT_DIR/main.py"
    else
        echo "No encuentro ni 'cleanboost' en PATH ni main.py junto al wrapper."
        echo "Ejecuta: pip install cleanboost"
        exit 1
    fi
fi
