#!/usr/bin/env bash
# Genera el informe Word a partir del JSON corregido en el revisor.
#
# Uso:
#   ./informe.sh [JSON] [DOCX]
#
# Por defecto usa <caso>/salidas/expediente_corregido.json si existe; si no,
# <caso>/salidas/expediente.json (sin correcciones humanas). La carpeta del caso
# la resuelve _caso.sh (variable CASO_DIR o la carpeta hermana con caso.json).

set -euo pipefail

DIRECTORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_caso.sh
source "$DIRECTORIO/_caso.sh"

if ! CASO="$(resolver_caso)"; then
    error_sin_caso
    exit 1
fi

SALIDAS="$CASO/salidas"
PYTHON="$DIRECTORIO/.venv/bin/python"
cd "$DIRECTORIO"

JSON="${1:-}"
if [ -z "$JSON" ]; then
    if [ -f "$SALIDAS/expediente_corregido.json" ]; then
        JSON="$SALIDAS/expediente_corregido.json"
    else
        JSON="$SALIDAS/expediente.json"
        echo "AVISO: no se encontro expediente_corregido.json."
        echo "       Se usara $JSON sin las correcciones del revisor."
    fi
fi

if [ ! -f "$JSON" ]; then
    echo "ERROR: no existe el archivo $JSON" >&2
    echo "Ejecute primero ./ejecutar.sh" >&2
    exit 1
fi

DOCX="${2:-$SALIDAS/informe.docx}"
PYTHONPATH=src "$PYTHON" -m documental.cli informe "$JSON" \
    --docx "$DOCX" --render "$SALIDAS/render"

echo "Abra el informe con LibreOffice o Word: $DOCX"
