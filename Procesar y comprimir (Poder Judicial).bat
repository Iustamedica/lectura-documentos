@echo off
REM Procesar y COMPRIMIR - para documentos que se suben al Poder Judicial
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo No se encontro el entorno de la herramienta (.venv).
  echo Pida a informatica (o ejecute instalar.bat) que la instale una vez.
  pause
  exit /b 1
)

echo Procesando y COMPRIMIENDO (para el Poder Judicial)... (puede tardar)
set "PYTHONPATH=src"
"%PY%" -m documental.cli expediente --carpeta "%~dp0Expediente" --ordenar --comprimir --abrir

echo.
pause
