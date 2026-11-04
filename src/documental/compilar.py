"""Compilacion del PDF unico que se presenta al tribunal.

Junta los documentos en un solo archivo, en el orden de la individualizacion, y
estampa en la primera pagina de cada uno el bloque de identificacion:

    DOCUMENTO N 3
    NOMBRE: GLORIA ESTER SOTO PEREZ
    RUT: 12.345.678-5
    TIPO: Bono de atencion FONASA           FECHA: 12-03-2026
    EMISOR: ...                             FOLIO: 1234

El encabezado se agrega ampliando la pagina hacia arriba, no encima del
contenido: el documento original nunca queda tapado y no se pierde ningun
margen del escaneo. Cada documento queda ademas como marcador del PDF para
poder saltar entre documentos en el visor.

Los archivos de origen solo se leen; nunca se modifican.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf

from .individualizacion import Grupo
from .ingesta import IMAGE_SUFFIXES, imagen_a_pdf

# Alto del encabezado estampado, en puntos (1 pulgada = 72 puntos).
HEADER_HEIGHT = 68.0
MARGEN = 12.0
TAMANO_FUENTE = 7.5
TAMANO_TITULO = 9.0
INTERLINEADO = 10.5


@dataclass
class ResultadoCompilacion:
    """Resumen de lo compilado (o de lo que se compilaria, en simulacion)."""

    destino: Path
    documentos: int = 0
    paginas: int = 0
    faltantes: list[str] = field(default_factory=list)
    grupos_sin_paginas: list[int] = field(default_factory=list)
    # Hojas que se repiten en el PDF porque contienen mas de un documento:
    # cada uno necesita su propio encabezado y su propia pagina.
    paginas_compartidas: list[str] = field(default_factory=list)
    dry_run: bool = False


def _indice(carpetas) -> dict[str, Path]:
    """Indice nombre de archivo -> ruta, para resolver ``source_file``."""
    indice: dict[str, Path] = {}
    for carpeta in carpetas:
        carpeta = Path(carpeta)
        if carpeta.is_file():
            indice.setdefault(carpeta.name, carpeta)
            continue
        if not carpeta.is_dir():
            continue
        for ruta in carpeta.iterdir():
            if ruta.is_file():
                indice.setdefault(ruta.name, ruta)
    return indice


def _abrir(ruta: Path, tempdir: Path) -> pymupdf.Document:
    """Abre un PDF; si el origen es una imagen, la convierte a PDF temporal."""
    if ruta.suffix.lower() in IMAGE_SUFFIXES:
        temporal = tempdir / f"{ruta.stem}.pdf"
        imagen_a_pdf([ruta], temporal)
        return pymupdf.open(str(temporal))
    return pymupdf.open(str(ruta))


def _lineas_encabezado(grupo: Grupo) -> list[str]:
    """Lineas del bloque de identificacion estampado sobre el documento."""
    lineas = [f"DOCUMENTO N {grupo.numero}"]
    nombre = grupo.valor("titular_nombre")
    rut = grupo.valor("titular_rut")
    if nombre:
        lineas.append(f"NOMBRE: {nombre}")
    if rut:
        lineas.append(f"RUT: {rut}")

    primera = []
    if grupo.tipo:
        primera.append(f"TIPO: {grupo.tipo}")
    if grupo.fecha_texto:
        primera.append(f"FECHA: {grupo.fecha_texto}")
    if primera:
        lineas.append("      ".join(primera))

    segunda = []
    emisor = grupo.valor("emisor_nombre")
    folio = grupo.valor("folio")
    if emisor:
        segunda.append(f"EMISOR: {emisor}")
    if folio:
        segunda.append(f"FOLIO: {folio}")
    if segunda:
        lineas.append("      ".join(segunda))
    return lineas


def _estampar(pagina: pymupdf.Page, grupo: Grupo, alto: float) -> None:
    """Escribe el bloque de identificacion en la franja superior de la pagina."""
    y = MARGEN + TAMANO_FUENTE
    for posicion, linea in enumerate(_lineas_encabezado(grupo)):
        if posicion == 0:
            pagina.insert_text(
                (MARGEN, y), linea, fontsize=TAMANO_TITULO, fontname="hebo"
            )
            y += INTERLINEADO + 2.0
        else:
            pagina.insert_text((MARGEN, y), linea, fontsize=TAMANO_FUENTE, fontname="helv")
            y += INTERLINEADO
    pagina.draw_line(
        pymupdf.Point(0.0, alto - 3.0),
        pymupdf.Point(pagina.rect.width, alto - 3.0),
        color=(0.55, 0.55, 0.55),
        width=0.6,
    )


def compilar(
    grupos: list[Grupo],
    *,
    origen,
    destino: Path,
    estampar: bool = True,
    dry_run: bool = False,
) -> ResultadoCompilacion:
    """Compila los documentos de ``grupos`` en un unico PDF.

    ``origen`` es una carpeta (o lista de carpetas) donde estan los archivos
    citados en ``source_file``. En ``dry_run`` solo se informa que se haria y
    que archivos faltan, sin escribir nada.
    """
    if not grupos:
        raise ValueError("No hay documentos para compilar")
    if isinstance(origen, (str, Path)):
        origen = [origen]

    destino = Path(destino)
    indice = _indice(origen)
    resultado = ResultadoCompilacion(destino=destino, dry_run=dry_run)

    def _ruta_de(grupo: Grupo) -> Path | None:
        encontrada = indice.get(grupo.archivo)
        if encontrada is not None:
            return encontrada
        candidata = Path(grupo.archivo)
        return candidata if candidata.is_file() else None

    if dry_run:
        for grupo in grupos:
            if _ruta_de(grupo) is None:
                resultado.faltantes.append(grupo.archivo)
                continue
            resultado.documentos += 1
            resultado.paginas += len(grupo.paginas)
        return resultado

    destino.parent.mkdir(parents=True, exist_ok=True)
    salida = pymupdf.open()
    marcadores: list[list] = []
    vistas: dict[str, int] = {}
    try:
        with tempfile.TemporaryDirectory() as temporal:
            tempdir = Path(temporal)
            for grupo in grupos:
                ruta = _ruta_de(grupo)
                if ruta is None:
                    resultado.faltantes.append(grupo.archivo)
                    continue
                for numero in grupo.paginas:
                    llave = f"{grupo.archivo} p.{numero}"
                    vistas[llave] = vistas.get(llave, 0) + 1
                    if vistas[llave] == 2:
                        resultado.paginas_compartidas.append(llave)
                fuente = _abrir(ruta, tempdir)
                try:
                    inicio = salida.page_count
                    for posicion, numero in enumerate(grupo.paginas):
                        indice_pagina = numero - 1
                        if not 0 <= indice_pagina < fuente.page_count:
                            continue
                        area = fuente[indice_pagina].rect
                        alto = HEADER_HEIGHT if (estampar and posicion == 0) else 0.0
                        nueva = salida.new_page(
                            width=area.width, height=area.height + alto
                        )
                        nueva.show_pdf_page(
                            pymupdf.Rect(0.0, alto, area.width, area.height + alto),
                            fuente,
                            indice_pagina,
                        )
                        if alto:
                            _estampar(nueva, grupo, alto)
                    agregadas = salida.page_count - inicio
                finally:
                    fuente.close()

                if agregadas <= 0:
                    resultado.grupos_sin_paginas.append(grupo.numero)
                    continue
                resultado.documentos += 1
                descripcion = f"{grupo.etiqueta} - {grupo.tipo}"
                if grupo.fecha_texto:
                    descripcion += f" - {grupo.fecha_texto}"
                marcadores.append([1, descripcion, inicio + 1])

        resultado.paginas = salida.page_count
        if marcadores:
            salida.set_toc(marcadores)
        salida.save(str(destino), garbage=3, deflate=True)
    finally:
        salida.close()
    return resultado
