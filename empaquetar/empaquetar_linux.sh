#!/usr/bin/env bash
# Construye el ejecutable de Linux (carpeta + ZIP).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv-build" ]; then
    python3 -m venv .venv-build
fi
# shellcheck disable=SC1091
source .venv-build/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r empaquetar/requirements-build.txt

if ! python -c "import tkinter" >/dev/null 2>&1; then
    echo "AVISO: falta Tkinter en este sistema." >&2
    echo "       En Debian/Ubuntu: sudo apt install python3-tk" >&2
    echo "       Sin Tkinter el ejecutable no podra abrir la ventana." >&2
fi

python -m PyInstaller --noconfirm --clean empaquetar/documental.spec

if command -v zip >/dev/null 2>&1; then
    (cd dist && zip -r -q LectorDeDocumentos-linux.zip LectorDeDocumentos)
    echo "LISTO: dist/LectorDeDocumentos-linux.zip"
else
    echo "LISTO: dist/LectorDeDocumentos/ (instale 'zip' para generar el ZIP)"
fi
