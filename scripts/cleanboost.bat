@echo off
REM cleanboost.bat — wrapper de doble-clic para Windows.
REM Abre cmd.exe con el menú 3 botones de CleanBoost.
REM Editar a "cleanboost --quick" si quieres silent mode.

where cleanboost >nul 2>nul
if %ERRORLEVEL% == 0 (
    cleanboost
) else (
    REM Fallback: ejecutar el script local main.py si existe.
    if exist "%~dp0main.py" (
        python "%~dp0main.py"
    ) else (
        echo No encuentro ni 'cleanboost' en PATH ni main.py junto al wrapper.
        echo Ejecuta: pip install cleanboost
        pause
        exit /b 1
    )
)
