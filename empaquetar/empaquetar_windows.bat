@echo off
REM Construye el ejecutable de Windows (carpeta + ZIP).
REM Requiere Python 3.10+ instalado en el equipo de compilacion.
setlocal
cd /d "%~dp0.."

where py >nul 2>nul
if %errorlevel%==0 (
  set "BASE=py -3.11"
) else (
  set "BASE=python"
)

if not exist ".venv-build\Scripts\python.exe" (
  %BASE% -m venv .venv-build
)
call .venv-build\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r empaquetar\requirements-build.txt
if errorlevel 1 goto :error

python -m PyInstaller --noconfirm --clean empaquetar\documental.spec
if errorlevel 1 goto :error

powershell -NoProfile -Command "Compress-Archive -Force -Path 'dist\LectorDeDocumentos\*' -DestinationPath 'dist\LectorDeDocumentos-windows.zip'"
if errorlevel 1 goto :error

echo.
echo LISTO: dist\LectorDeDocumentos-windows.zip
echo Descomprima ese ZIP y haga doble clic en "Lector de documentos.exe".
pause
exit /b 0

:error
echo.
echo FALLO el empaquetado. Revise el mensaje anterior.
pause
exit /b 1
