#!/usr/bin/env bash
# Flujo completo en un solo paso:
#   1) OCR + extraccion de la carpeta de escaneos
#   2) generacion del revisor HTML
#
# Uso:
#   ./ejecutar.sh [CARPETA_ESCANEOS]
#
# Los documentos del paciente, su caso.json y las salidas viven FUERA de este
# repositorio, en la carpeta del caso (vease _caso.sh). Asi nada con datos
# clinicos entra a git. Se puede fijar a mano con CASO_DIR:
#
#   CASO_DIR="/ruta/al/caso" ./ejecutar.sh
#
# Despues de correr esto:
#   - abrir <caso>/salidas/revision.html en el navegador y corregir
#   - exportar "expediente_corregido.json" dentro de <caso>/salidas/
#   - ./informe.sh   (Word)  y  ./compilar.sh   (PDF + individualizacion)

set -euo pipefail

DIRECTORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_caso.sh
source "$DIRECTORIO/_caso.sh"

if ! CASO="$(resolver_caso)"; then
    error_sin_caso
    exit 1
fi

ESCANEOS="${1:-$CASO/escaneos-csm}"
SALIDAS="$CASO/salidas"
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
    echo "Indiquela como argumento o ajuste CASO_DIR." >&2
    exit 1
fi

if [ -f "$CASO/caso.json" ]; then
    TITULARES=(--titulares "$CASO/caso.json")
else
    echo "AVISO: no hay $CASO/caso.json; se procesa sin titulares declarados." >&2
    TITULARES=()
fi

cd "$DIRECTORIO"
mkdir -p "$SALIDAS"

echo "== 1/2 Procesando escaneos de: $ESCANEOS"
echo "   Salidas en: $SALIDAS"
echo "   (puede tardar varios minutos; el progreso del OCR se muestra al final)"
PYTHONPATH=src "$PYTHON" -m documental.cli procesar "$ESCANEOS" \
    --perfil salud \
    --json "$SALIDAS/expediente.json" \
    --render "$SALIDAS/render" \
    --html "$SALIDAS/revision.html" \
    ${TITULARES[@]+"${TITULARES[@]}"} \
    --image-prefix render/

echo
echo "== 2/2 Listo."
echo "   Siguiente paso: abrir $SALIDAS/revision.html, corregir y exportar"
echo "   'expediente_corregido.json' dentro de $SALIDAS/. Luego ./informe.sh"
