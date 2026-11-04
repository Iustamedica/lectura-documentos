#!/usr/bin/env bash
# Compila el PDF unico para el tribunal y la tabla de individualizacion.
#
# Uso:
#   ./compilar.sh [JSON] [CARPETA_ORIGEN] [PREFIJO]
#
# Por defecto:
#   JSON           = <caso>/salidas/expediente_corregido.json (o expediente.json)
#   CARPETA_ORIGEN = <caso>/salidas/pdf  (los PDF de `preparar`), si no existe se
#                    usa la carpeta de escaneos del caso
#   PREFIJO        = documentos
#
# Genera <caso>/salidas/<PREFIJO>.pdf, <PREFIJO>-individualizacion.csv y .docx

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
    echo "ERROR: no existe el expediente $JSON" >&2
    echo "Ejecute primero ./ejecutar.sh" >&2
    exit 1
fi

ORIGEN="${2:-}"
if [ -z "$ORIGEN" ]; then
    if [ -d "$SALIDAS/pdf" ]; then
        ORIGEN="$SALIDAS/pdf"
    else
        ORIGEN="$CASO/escaneos-csm"
    fi
fi

if [ ! -d "$ORIGEN" ]; then
    echo "ERROR: no existe la carpeta de origen: $ORIGEN" >&2
    exit 1
fi

PREFIJO="${3:-documentos}"

echo "== Compilando desde: $JSON"
echo "   Archivos originales: $ORIGEN"
PYTHONPATH=src "$PYTHON" -m documental.cli compilar "$JSON" \
    --origen "$ORIGEN" \
    --pdf "$SALIDAS/$PREFIJO.pdf" \
    --csv "$SALIDAS/$PREFIJO-individualizacion.csv" \
    --docx "$SALIDAS/$PREFIJO-individualizacion.docx"

echo
echo "Listo. Revise antes de presentar:"
echo "   $SALIDAS/$PREFIJO.pdf"
echo "   $SALIDAS/$PREFIJO-individualizacion.csv"
echo "   $SALIDAS/$PREFIJO-individualizacion.docx"
