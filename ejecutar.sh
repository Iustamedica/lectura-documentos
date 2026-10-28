#!/usr/bin/env bash
# Flujo completo en un solo paso:
#   1) OCR + extraccion de la carpeta de escaneos
#   2) generacion del revisor HTML
#
# Uso:
#   ./ejecutar.sh [CARPETA_ESCANEOS]
#
# Despues de correr esto:
#   - abrir salidas/revision.html en el navegador y corregir
#   - exportar "expediente_corregido.json" dentro de salidas/
#   - ./informe.sh   (genera el Word a partir del JSON corregido)

set -euo pipefail

DIRECTORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ESCANEOS="${1:-$DIRECTORIO/../../escaneos-csm}"
PYTHON="$DIRECTORIO/.venv/bin/python"

if [ ! -x "$PYTHON" ]; then
    echo "ERROR: no existe el entorno virtual." >&2
    echo "Creelo con:" >&2
    echo "  cd \"$DIRECTORIO\"" >&2
    echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
    exit 1
fi

if [ ! -d "$ESCANEOS" ]; then
    echo "ERROR: no existe la carpeta de escaneos: $ESCANEOS" >&2
    exit 1
fi

cd "$DIRECTORIO"
mkdir -p salidas

echo "== 1/2 Procesando escaneos de: $ESCANEOS"
echo "   (puede tardar varios minutos; el progreso del OCR se muestra al final)"
PYTHONPATH=src "$PYTHON" -m documental.cli procesar "$ESCANEOS" \
    --json salidas/expediente.json \
    --render salidas/render \
    --html salidas/revision.html \
    --titulares caso.json \
    --image-prefix render/

echo
echo "== 2/2 Listo."
echo "   Siguiente paso: abrir salidas/revision.html, corregir y exportar"
echo "   'expediente_corregido.json' dentro de salidas/. Luego ejecutar ./informe.sh"
