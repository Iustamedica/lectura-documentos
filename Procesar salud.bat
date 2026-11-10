@echo off
REM Procesar documentos - MODO SALUD (opcional, Windows)
REM Deje sus fotos y PDF en: Expediente\1. Documentos a procesar
REM Los resultados aparecen en: Expediente\Resultados
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo No se encontro el entorno de la herramienta (.venv).
  echo Pida a informatica (o ejecute instalar.bat) que la instale una vez.
  pause
  exit /b 1
)

echo Procesando documentos en modo SALUD... (puede tardar; no cierre esta ventana)
set "PYTHONPATH=src"
"%PY%" -m documental.cli expediente --carpeta "%~dp0Expediente" --perfil salud --abrir

echo.
pause
