#!/usr/bin/env bash
# Genera el informe Word a partir del JSON corregido en el revisor.
#
# Uso:
#   ./informe.sh [JSON] [DOCX]
#
# Por defecto usa salidas/expediente_corregido.json si existe; si no,
# salidas/expediente.json (sin correcciones humanas).

set -euo pipefail

DIRECTORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$DIRECTORIO/.venv/bin/python"
cd "$DIRECTORIO"

JSON="${1:-}"
if [ -z "$JSON" ]; then
    if [ -f salidas/expediente_corregido.json ]; then
        JSON="salidas/expediente_corregido.json"
    else
        JSON="salidas/expediente.json"
        echo "AVISO: no se encontro salidas/expediente_corregido.json."
        echo "       Se usara $JSON sin las correcciones del revisor."
    fi
fi

if [ ! -f "$JSON" ]; then
    echo "ERROR: no existe el archivo $JSON" >&2
    echo "Ejecute primero ./ejecutar.sh" >&2
    exit 1
fi

DOCX="${2:-salidas/informe.docx}"
PYTHONPATH=src "$PYTHON" -m documental.cli informe "$JSON" \
    --docx "$DOCX" --render salidas/render

echo "Abra el informe con LibreOffice o Word: $DOCX"
