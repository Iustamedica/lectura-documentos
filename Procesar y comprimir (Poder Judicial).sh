#!/usr/bin/env bash
# Procesar y COMPRIMIR — para documentos que se suben al Poder Judicial
# Deje sus fotos y PDF en: Expediente/1. Documentos a procesar
# Genera los PDF con menor peso (limite PJ: 10 MB por archivo / 30 MB total).
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

echo "Procesando y COMPRIMIENDO (para el Poder Judicial)... (puede tardar)"
PYTHONPATH=src "$PY" -m documental.cli expediente --carpeta "$DIR/Expediente" --ordenar --comprimir --abrir

echo
read -n 1 -r -p "Proceso terminado. Presione una tecla para cerrar..."
