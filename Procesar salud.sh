#!/usr/bin/env bash
# Procesar documentos — MODO SALUD (opcional, Linux / Mac)
# Deje sus fotos y PDF en: Expediente/1. Documentos a procesar
# Los resultados aparecen en: Expediente/Resultados
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PY=".venv/bin/python"
if [ ! -x "$PY" ]; then
  echo "No se encontro el entorno de la herramienta (.venv)."
  echo "Pida a informatica (o ejecute 'instalar.sh') que la instale una vez."
  read -n 1 -r -p "Presione una tecla para cerrar..."
  exit 1
fi

echo "Procesando documentos en modo SALUD... (puede tardar; no cierre esta ventana)"
PYTHONPATH=src "$PY" -m documental.cli expediente --carpeta "$DIR/Expediente" --perfil salud --abrir

echo
read -n 1 -r -p "Proceso terminado. Presione una tecla para cerrar..."
