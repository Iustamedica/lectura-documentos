#!/usr/bin/env bash
# Instalacion (una sola vez) - Linux / macOS
# Crea (o repara) el entorno .venv de la herramienta. Lo ejecuta una persona con
# conocimientos basicos (o informatica) una vez; despues se usa "Procesar documentos".
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PY=python3
if ! command -v "$PY" >/dev/null 2>&1; then
  echo "No se encontro Python 3. Instale Python 3.10 o superior y reintente."
  if [ -t 0 ]; then read -n 1 -r -p "Presione una tecla para cerrar..."; fi
  exit 1
fi

if ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "Se requiere Python 3.10 o superior (encontrado: $("$PY" --version 2>&1))."
  if [ -t 0 ]; then read -n 1 -r -p "Presione una tecla para cerrar..."; fi
  exit 1
fi

if ! "$PY" -c 'import tkinter' >/dev/null 2>&1; then
  echo "Aviso: no se encontro Tkinter (necesario para la ventana de la aplicacion)."
  if command -v brew >/dev/null 2>&1; then
    echo "  En macOS: brew install python-tk"
  elif command -v apt-get >/dev/null 2>&1; then
    echo "  En Linux: sudo apt install python3-tk"
  else
    echo "  Instale el paquete Tkinter de su sistema y vuelva a ejecutar este script."
  fi
fi

# Repara un entorno viejo o incompleto (por ejemplo, si cambio la version de Python).
if [ -x .venv/bin/python ] && .venv/bin/python -c 'import pymupdf, docx, rapidocr, onnxruntime, PIL' >/dev/null 2>&1; then
  echo "El entorno .venv ya esta listo."
else
  echo "Creando el entorno (.venv)..."
  rm -rf .venv
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  echo "Instalando dependencias (puede tardar varios minutos)..."
  .venv/bin/python -m pip install -r requirements.txt
fi

echo
echo "Instalacion lista."
echo "Los modelos de OCR vienen incluidos: no necesita internet para procesar."
if [ -t 0 ]; then read -n 1 -r -p "Presione una tecla para cerrar..."; fi

