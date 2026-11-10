@echo off
REM Instalacion (una sola vez) - Windows
REM Crea el entorno de la herramienta. Lo ejecuta informatica una vez.
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instale Python 3.10 o superior y reintente.
  pause
  exit /b 1
)

echo Creando entorno (.venv)...
python -m venv .venv
call .venv\Scripts\python.exe -m pip install --upgrade pip
echo Instalando dependencias (puede tardar varios minutos)...
call .venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Instalacion lista.
echo Los modelos de OCR vienen incluidos: no necesita internet para procesar.
pause
