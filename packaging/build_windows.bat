@echo off
REM =====================================================
REM build_windows.bat - CLEANBOOST v3.1.1 Windows installer builder
REM Compila main.py + daemon.py en un .exe portable con PyInstaller.
REM Output:  dist\cleanboost.exe  +  dist\cleanboost.bat (wrapper doble-click)
REM =====================================================

setlocal
set VERSION=3.1.1
set APPNAME=cleanboost

echo.
echo [CLEANBOOST] Build Windows installer v%VERSION%
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python no encontrado en PATH. Instala Python 3.8+ desde python.org
    exit /b 1
)

if exist "build_venv\" (
    rmdir /s /q build_venv
)
echo [CLEANBOOST] Creando venv en build_venv\...
python -m venv build_venv
call build_venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install "pyinstaller>=6.0"

if exist "dist\" rmdir /s /q dist
if exist "build\" rmdir /s /q build
if exist "%APPNAME%.spec" del /q %APPNAME%.spec


REM =====================================================
REM Preflight: check Pillow is available for icon generation.
REM packaging/make_icon.py requires PIL. If absent, fail fast.
REM =====================================================
python -c "import PIL" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Pillow no instalado. install: python -m pip install --user Pillow
    echo        (solo necesario si quieres generar cleanboost.ico via packaging\make_icon.py)
)

echo [CLEANBOOST] Compilando %APPNAME%.exe (one-file, console)...
pyinstaller ^
    --onefile ^
    --console ^
    --name %APPNAME% ^
    --add-data "scripts;scripts" ^
    --add-data "packaging;packaging" ^
    main.py

if exist "dist\%APPNAME%.exe" (
    copy /Y scripts\cleanboost.bat dist\cleanboost.bat >nul
    echo.
    echo [CLEANBOOST] Build exitoso!
    echo    Ejecutable:    dist\%APPNAME%.exe
    echo    Wrapper doble-click: dist\cleanboost.bat
) else (
    echo [ERROR] PyInstaller fallo. Revisa el log arriba.
    exit /b 1
)

endlocal
