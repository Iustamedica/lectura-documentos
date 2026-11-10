#!/usr/bin/env bash
# Abre la mini app (Linux / Mac). Doble clic o: ./"Lector de documentos.sh"
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No se encontro el entorno (.venv). Ejecute primero 'instalar.sh'."
  read -n 1 -r -p "Presione una tecla para cerrar..."
  exit 1
fi

PYTHONPATH=src "$PY" -m documental.gui
