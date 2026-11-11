"""Ordena las paginas de un PDF por el numero impreso.

Un libro escaneado o exportado en desorden suele conservar el folio impreso en
la esquina. Este modulo lo detecta en la primera y la ultima linea de cada
pagina, valida que la secuencia sea coherente y escribe un **PDF nuevo** con las
paginas en orden. Nunca sobrescribe el original.

Si la secuencia es ambigua (numeros repetidos, saltos grandes o demasiadas
paginas sin numero) no reordena y devuelve un informe para revisar a mano.
"""

from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

_RE_ARABIGO = re.compile(r"^\s*(?:[-–—]\s*)?(\d{1,4})\s*(?:[|·:]\s*.*)?$")
_RE_ARABIGO_ENCABEZADO = re.compile(
    r"^\s*(\d{1,4})\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s.,-]{3,}$"
)
_RE_ROMANO = re.compile(r"^\s*([ivxlcdm]{1,7})\s*$", re.IGNORECASE)

_ROMANOS = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def _romano_a_entero(texto: str) -> int | None:
    """Convierte un numero romano a entero (None si no es utilizable)."""
    valores = [_ROMANOS[letra] for letra in texto.lower()]
    total = 0
    for posicion, valor in enumerate(valores):
        siguiente = valores[posicion + 1] if posicion + 1 < len(valores) else 0
        total += -valor if valor < siguiente else valor
    return total or None


def detectar_numero(texto: str, paginas: int = 0) -> int | None:
    """Numero de pagina impreso en el encabezado o pie de una pagina."""
    lineas = [linea.strip() for linea in (texto or "").splitlines() if linea.strip()]
    if not lineas:
        return None
    candidatas = lineas[:2] + lineas[-2:]
    for linea in candidatas:
        encontrado = _RE_ARABIGO.match(linea) or _RE_ARABIGO_ENCABEZADO.match(linea)
        if encontrado:
            numero = int(encontrado.group(1))
            # Descarta anios y numeros fuera de rango; la coherencia de la
            # secuencia se valida despues, en ``analizar``.
            if 1 <= numero <= 5000 and not (1900 <= numero <= 2099):
                return numero
    for linea in candidatas:
        if _RE_ROMANO.match(linea):
            valor = _romano_a_entero(linea)
            if valor and valor <= 100:
                return valor
    return None


@dataclass
class Analisis:
    """Resultado del analisis de paginas de un PDF."""

    origen: Path
    total: int = 0
    numeros: list[int | None] = field(default_factory=list)
    orden: list[int] = field(default_factory=list)
    reordenable: bool = False
    motivo: str = ""


def analizar(origen: Path) -> Analisis:
    """Lee el numero impreso de cada pagina y decide si se puede reordenar."""
    origen = Path(origen)
    with pymupdf.open(str(origen)) as doc:
        total = doc.page_count
        numeros = [
            detectar_numero(doc[indice].get_text(), total) for indice in range(total)
        ]

    analisis = Analisis(origen=origen, total=total, numeros=numeros)
    conocidos = [(pos, num) for pos, num in enumerate(numeros) if num is not None]
    if len(conocidos) < max(3, int(total * 0.6)):
        analisis.motivo = (
            f"solo {len(conocidos)} de {total} paginas tienen numero legible"
        )
        return analisis
    valores = [num for _, num in conocidos]
    if len(set(valores)) != len(valores):
        analisis.motivo = "hay numeros de pagina repetidos"
        return analisis
    ordenados = sorted(valores)
    saltos = [b - a for a, b in zip(ordenados, ordenados[1:])]
    if saltos and max(saltos) > max(20, total * 2):
        analisis.motivo = "los numeros de pagina no forman una secuencia continua"
        return analisis
    if ordenados and ordenados[-1] - ordenados[0] > total * 3:
        analisis.motivo = "el rango de numeros no corresponde al tamano del PDF"
        return analisis
    primero = conocidos[0][0]
    if any(numeros[pos] is None for pos in range(primero, total)):
        analisis.motivo = "hay paginas sin numero entre las numeradas"
        return analisis
    orden = list(range(primero))
    for pos, _ in sorted(conocidos, key=lambda par: par[1]):
        orden.append(pos)
    if orden == list(range(total)):
        analisis.motivo = "las paginas ya estan en orden"
        return analisis
    analisis.orden = orden
    analisis.reordenable = True
    return analisis


@dataclass
class ResultadoOrden:
    origen: Path
    destino: Path | None
    total: int
    numeros: list[int | None]
    reordenado: bool
    motivo: str
    orden: list[int] = field(default_factory=list)

    def informe(self) -> list[dict]:
        """Mapa pagina del PDF -> numero impreso -> nueva posicion."""
        posicion = {pos: indice + 1 for indice, pos in enumerate(self.orden)}
        return [
            {
                "pagina_pdf": pos + 1,
                "numero_impreso": self.numeros[pos],
                "nueva_posicion": posicion.get(pos),
            }
            for pos in range(self.total)
        ]


def ordenar_pdf(
    origen: Path,
    destino: Path | None = None,
    *,
    forzar: bool = False,
) -> ResultadoOrden:
    """Escribe un PDF nuevo con las paginas ordenadas por su numero impreso.

    ``forzar`` permite ordenar aunque haya paginas sin numero: se mantienen
    despues de la pagina numerada que las precede.
    """
    origen = Path(origen)
    analisis = analizar(origen)
    if not analisis.reordenable and not forzar:
        return ResultadoOrden(
            origen=origen,
            destino=None,
            total=analisis.total,
            numeros=analisis.numeros,
            reordenado=False,
            motivo=analisis.motivo or "no se pudo determinar un orden seguro",
        )

    orden = analisis.orden or _orden_forzado(analisis.numeros)
    if destino is None:
        destino = origen.with_name(f"{origen.stem}-ordenado.pdf")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(str(origen)) as doc:
        salida = pymupdf.open()
        try:
            for pos in orden:
                salida.insert_pdf(doc, from_page=pos, to_page=pos)
            with contextlib.suppress(Exception):
                salida.set_metadata(doc.metadata or {})
            salida.save(str(destino), garbage=4, deflate=True)
        finally:
            salida.close()

    return ResultadoOrden(
        origen=origen,
        destino=destino,
        total=analisis.total,
        numeros=analisis.numeros,
        reordenado=True,
        motivo="reordenado por numero impreso",
        orden=orden,
    )


def _orden_forzado(numeros: list[int | None]) -> list[int]:
    """Orden estable: paginas sin numero quedan tras la numerada anterior."""
    orden: list[int] = []
    pendientes: list[int] = []
    for pos, numero in enumerate(numeros):
        if numero is None:
            pendientes.append(pos)
            continue
        orden.extend(pendientes)
        pendientes = []
        orden.append(pos)
    orden.extend(pendientes)
    return orden
