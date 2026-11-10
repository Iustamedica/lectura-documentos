@echo off
REM Abre la mini app (Windows). Doble clic.
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\pythonw.exe"
if not exist "%PY%" (
  echo No se encontro el entorno (.venv). Ejecute primero instalar.bat.
  pause
  exit /b 1
)

set "PYTHONPATH=src"
start "" "%PY%" -m documental.gui
