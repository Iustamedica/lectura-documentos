#!/usr/bin/env bash
# Instalacion (una sola vez) — Linux / Mac
# Crea el entorno de la herramienta. Lo ejecuta una persona con conocimientos
# basicos (o informatica) una vez; despues el abogado solo usa "Procesar documentos".
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "No se encontro Python 3. Instale Python 3.10 o superior y reintente."
  read -n 1 -r -p "Presione una tecla para cerrar..."; exit 1
fi

echo "Creando entorno (.venv)..."
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
echo "Instalando dependencias (puede tardar varios minutos)..."
.venv/bin/pip install -r requirements.txt

echo
echo "Instalacion lista."
echo "La PRIMERA vez que procese descargara los modelos de OCR (necesita internet)."
read -n 1 -r -p "Presione una tecla para cerrar..."
