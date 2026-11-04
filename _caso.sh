#!/usr/bin/env bash
# Resuelve la carpeta del caso: donde viven los documentos del paciente, su
# caso.json y las salidas. Se mantiene FUERA de este repositorio para que nada
# con datos clinicos entre a git.
#
# Prioridad:
#   1) la variable de entorno CASO_DIR, si esta definida;
#   2) la unica carpeta hermana del proyecto que contenga un caso.json.
#
# Si hay cero o varias candidatas, la funcion falla y el script pide CASO_DIR.
#
# Este archivo se usa con "source"; no se ejecuta por si solo.

CASO_DIRECTORIO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

resolver_caso() {
    if [ -n "${CASO_DIR:-}" ]; then
        printf '%s' "$CASO_DIR"
        return 0
    fi

    local base carpeta
    local candidatas=()
    base="$(cd "$CASO_DIRECTORIO/../../.." && pwd)" || return 1
    for carpeta in "$base"/*/; do
        if [ -f "${carpeta}caso.json" ]; then
            candidatas+=("${carpeta%/}")
        fi
    done

    if [ "${#candidatas[@]}" -eq 1 ]; then
        printf '%s' "${candidatas[0]}"
        return 0
    fi
    return 1
}

error_sin_caso() {
    echo "ERROR: no pude determinar la carpeta del caso." >&2
    echo "Defina la variable CASO_DIR apuntando a la carpeta que contiene" >&2
    echo "caso.json y las carpetas de escaneos. Ejemplo:" >&2
    echo '  CASO_DIR="/ruta/al/caso" ./ejecutar.sh' >&2
}
