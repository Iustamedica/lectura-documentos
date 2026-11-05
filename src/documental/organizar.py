"""Ordenamiento del expediente en categorias y documentos individuales.

Produce una carpeta (``V.1`` por convencion) con un arbol en el que cada
documento es un PDF propio, archivado segun su genero:

    V.1/
      01-bonos/00-bonos.pdf             consolidado de la categoria
      01-bonos/001 17-07-2023 Bono ... .pdf
      02-boletas/...
      03-fichas/CLINICA LOS ROBLES/...  una carpeta por prestador
      04-recetas/...
      05-certificados/...
      06-otros/...
      indice.csv                        tabla completa
      indice.docx                       tabla para el escrito
      expediente-refinado.json          expediente con los tipos normalizados
      LEEME.txt                         manifiesto de lo generado

Cada PDF individual lleva el mismo encabezado estampado del PDF compilado
(documento N, nombre, RUT, tipo, fecha, emisor, folio), de modo que la hoja
sigue siendo identificable aunque se la separe del expediente.

Los archivos de origen solo se leen; nunca se mueven ni se modifican.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from docx import Document as DocxDocument
from docx.shared import Pt

from .categorias import (
    CAT_FICHAS,
    CATEGORIA_CARPETA,
    CATEGORIA_ETIQUETA,
    CATEGORIAS,
    ORDEN_CATEGORIA,
    Prestador,
    carpeta_de,
    detalle_de,
    limpiar_nombre,
    nombre_archivo,
    prestador_de,
    refinar,
)
from .compilar import (
    CALIDAD_JPEG,
    DPI_COMPRESION,
    HEADER_HEIGHT,
    _abrir,
    _estampar,
    _indice,
)
from .individualizacion import Grupo, agrupar, filas
from .models import Document

# Nombre del PDF consolidado de cada categoria (va primero en la carpeta).
CONSOLIDADO = "00-{clave}.pdf"


@dataclass
class ResultadoOrden:
    """Resumen de lo ordenado (o de lo que se ordenaria, en simulacion)."""

    destino: Path
    documentos: int = 0
    paginas: int = 0
    por_categoria: dict[str, int] = field(default_factory=dict)
    por_prestador: dict[str, int] = field(default_factory=dict)
    sin_prestador: int = 0
    sin_clasificar: int = 0
    compartidas: list[str] = field(default_factory=list)
    faltantes: list[str] = field(default_factory=list)
    dry_run: bool = False
    bytes: int = 0


def _ruta_de(archivo: str, indice: dict[str, Path]) -> Path | None:
    encontrada = indice.get(archivo)
    if encontrada is not None:
        return encontrada
    candidata = Path(archivo)
    return candidata if candidata.is_file() else None


def _destino_de(
    grupo: Grupo, raiz: Path, prestadores: tuple[Prestador, ...] | None
) -> tuple[str, str, Path]:
    """Categoria, subcarpeta y ruta del PDF individual de un grupo."""
    from .categorias import fecha_texto

    categoria = grupo.categoria
    carpeta = raiz / CATEGORIA_CARPETA.get(categoria, "06-otros")

    subcarpeta = ""
    if categoria == CAT_FICHAS:
        # El prestador puede estar solo en una de las hojas del documento.
        for documento in grupo.documentos:
            subcarpeta = prestador_de(documento, prestadores)
            if subcarpeta:
                break
        carpeta = carpeta / carpeta_de(subcarpeta)

    nombre = nombre_archivo(
        grupo.numero,
        grupo.tipo,
        fecha_texto(grupo.primero),
        grupo.valor("titular_nombre"),
        grupo.valor("folio"),
    )
    return categoria, subcarpeta, carpeta / nombre


def _escribir_grupo(
    grupo: Grupo,
    fuente: pymupdf.Document,
    destino: Path,
    *,
    estampar: bool,
) -> int:
    """Escribe el PDF de un documento y devuelve las paginas agregadas."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    salida = pymupdf.open()
    agregadas = 0
    try:
        for posicion, numero in enumerate(grupo.paginas):
            indice_pagina = numero - 1
            if not 0 <= indice_pagina < fuente.page_count:
                continue
            area = fuente[indice_pagina].rect
            alto = HEADER_HEIGHT if (estampar and posicion == 0) else 0.0
            pagina = salida.new_page(width=area.width, height=area.height + alto)
            pagina.show_pdf_page(
                pymupdf.Rect(0.0, alto, area.width, area.height + alto),
                fuente,
                indice_pagina,
            )
            if alto:
                _estampar(pagina, grupo, alto)
            agregadas += 1
        if agregadas:
            salida.save(str(destino), garbage=3, deflate=True)
    finally:
        salida.close()
    return agregadas


def ordenar(
    grupos: list[Grupo],
    *,
    origen,
    destino: Path,
    estampar: bool = True,
    comprimir: bool = False,
    dpi: int = DPI_COMPRESION,
    calidad: int = CALIDAD_JPEG,
    prestadores: tuple[Prestador, ...] | None = None,
    dry_run: bool = False,
) -> ResultadoOrden:
    """Escribe el arbol de carpetas por categoria con un PDF por documento.

    ``origen`` es una carpeta (o lista) donde estan los archivos citados en
    ``source_file``. Los grupos ya vienen refinados y numerados por
    ``individualizacion.agrupar``; aqui solo se decide en que carpeta va cada
    documento y se escribe.
    """
    if not grupos:
        raise ValueError("No hay documentos para ordenar")
    if isinstance(origen, (str, Path)):
        origen = [origen]

    destino = Path(destino)
    indice = _indice(origen)
    resultado = ResultadoOrden(destino=destino, dry_run=dry_run)

    # Un mismo PDF de origen puede contener documentos de varias categorias, por
    # lo que se agrupa por archivo para abrirlo una sola vez.
    por_archivo: dict[str, list[Grupo]] = {}
    for grupo in grupos:
        por_archivo.setdefault(grupo.archivo, []).append(grupo)

    usados: set[Path] = set()
    consolidados: dict[str, pymupdf.Document] = {}
    try:
        with tempfile.TemporaryDirectory() as temporal:
            tempdir = Path(temporal)
            for archivo, lista in por_archivo.items():
                ruta = _ruta_de(archivo, indice)
                if ruta is None:
                    resultado.faltantes.append(archivo)
                    continue
                fuente = _abrir(ruta, tempdir)
                try:
                    for grupo in sorted(lista, key=lambda g: g.numero):
                        categoria, subcarpeta, ruta_pdf = _destino_de(
                            grupo, destino, prestadores
                        )
                        resultado.por_categoria[categoria] = (
                            resultado.por_categoria.get(categoria, 0) + 1
                        )
                        if categoria == CAT_FICHAS:
                            llave = subcarpeta or "SIN PRESTADOR"
                            resultado.por_prestador[llave] = (
                                resultado.por_prestador.get(llave, 0) + 1
                            )
                            if not subcarpeta:
                                resultado.sin_prestador += 1
                        if categoria == "otros" and grupo.tipo == "Documento sin clasificar":
                            resultado.sin_clasificar += 1
                        for numero in grupo.paginas:
                            llave = f"{grupo.archivo} p.{numero}"
                            if llave in usados:
                                resultado.compartidas.append(llave)
                            usados.add(llave)
                        if dry_run:
                            resultado.documentos += 1
                            resultado.paginas += len(grupo.paginas)
                            continue
                        # Dos documentos distintos no pueden compartir nombre.
                        while ruta_pdf in usados or ruta_pdf.exists():
                            ruta_pdf = ruta_pdf.with_name(
                                f"{ruta_pdf.stem}-bis{ruta_pdf.suffix}"
                            )
                        usados.add(ruta_pdf)
                        agregadas = _escribir_grupo(
                            grupo, fuente, ruta_pdf, estampar=estampar
                        )
                        if not agregadas:
                            continue
                        resultado.documentos += 1
                        resultado.paginas += agregadas
                        consolidado = consolidados.get(categoria)
                        if consolidado is None:
                            consolidado = pymupdf.open()
                            consolidados[categoria] = consolidado
                        with pymupdf.open(str(ruta_pdf)) as escrito:
                            consolidado.insert_pdf(escrito)
                finally:
                    fuente.close()
    finally:
        for categoria, consolidado in consolidados.items():
            try:
                if consolidado.page_count:
                    carpeta = destino / CATEGORIA_CARPETA.get(categoria, "06-otros")
                    carpeta.mkdir(parents=True, exist_ok=True)
                    ruta = carpeta / CONSOLIDADO.format(clave=categoria)
                    if comprimir:
                        consolidado.rewrite_images(
                            dpi_threshold=max(1, int(dpi)) + 1,
                            dpi_target=max(1, int(dpi)),
                            quality=calidad,
                            lossy=True,
                            lossless=True,
                        )
                    consolidado.save(str(ruta), garbage=3, deflate=True)
            finally:
                consolidado.close()

    if not dry_run:
        resultado.bytes = sum(
            ruta.stat().st_size for ruta in destino.rglob("*.pdf") if ruta.is_file()
        )
    return resultado


def agrupar_refinado(
    documentos: list[Document],
    prestadores: tuple[Prestador, ...] | None = None,
) -> list[Grupo]:
    """Refina los documentos (tipo canonico y datos faltantes) y los agrupa."""
    for documento in documentos:
        refinar(documento, prestadores=prestadores)
    return agrupar(documentos)


def _columnas_csv() -> list[str]:
    return [
        "N",
        "categoria",
        "tipo",
        "fecha",
        "emisor",
        "rut_emisor",
        "titular",
        "rut_titular",
        "folio",
        "monto_total",
        "detalle",
        "archivo",
        "pagina",
        "confianza",
    ]


def escribir_indice_csv(grupos: list[Grupo], path: Path) -> Path:
    """Indice completo de los documentos ordenados (separador ``;`` para Excel)."""
    import csv

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columnas = _columnas_csv()
    with path.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        for fila in filas(grupos):
            escritor.writerow({clave: fila.get(clave, "") for clave in columnas})
    return path


def _tabla(documento, grupos: list[Grupo], columnas) -> None:
    """Agrega al Word la tabla de una categoria."""
    tabla = documento.add_table(rows=1, cols=len(columnas))
    tabla.style = "Table Grid"
    for celda, (_, etiqueta) in zip(tabla.rows[0].cells, columnas):
        celda.text = ""
        corrida = celda.paragraphs[0].add_run(etiqueta)
        corrida.bold = True
        corrida.font.size = Pt(8)
    for fila in filas(grupos):
        celdas = tabla.add_row().cells
        for celda, (clave, _) in zip(celdas, columnas):
            celda.text = ""
            corrida = celda.paragraphs[0].add_run(fila.get(clave) or "-")
            corrida.font.size = Pt(8)


def escribir_indice_docx(
    grupos: list[Grupo],
    path: Path,
    *,
    titulo: str = "Indice de documentos por categoria",
) -> Path:
    """Indice en Word, con una seccion y una tabla por categoria."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    documento = DocxDocument()
    documento.add_heading(titulo, level=1)
    documento.add_paragraph(
        f"Total de documentos: {len(grupos)}. Cada documento del PDF compilado "
        "conserva el mismo numero que aparece en esta tabla."
    )

    from .individualizacion import COLUMNAS

    for clave, etiqueta, _ in CATEGORIAS:
        del_grupo = [g for g in grupos if g.categoria == clave]
        if not del_grupo:
            continue
        documento.add_heading(f"{etiqueta} ({len(del_grupo)})", level=2)
        _tabla(documento, del_grupo, COLUMNAS)
        documento.add_paragraph("")

    documento.save(str(path))
    return path


def escribir_leeme(
    resultado: ResultadoOrden,
    path: Path,
    *,
    origen: list[str] | None = None,
) -> Path:
    """Manifiesto de lo generado, para que el expediente sea reproducible."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lineas = [
        "EXPEDIENTE ORDENADO POR CATEGORIA",
        "=================================",
        "",
        f"Documentos: {resultado.documentos}   Paginas: {resultado.paginas}",
        f"Carpeta: {resultado.destino}",
    ]
    if origen:
        lineas.append("Origen: " + ", ".join(origen))
    lineas += ["", "Documentos por categoria:"]
    for clave, etiqueta, carpeta in CATEGORIAS:
        total = resultado.por_categoria.get(clave, 0)
        if total:
            lineas.append(f"  {carpeta:16s} {total:4d}  {etiqueta}")

    if resultado.por_prestador:
        lineas += ["", "Fichas por prestador:"]
        for prestador, total in sorted(resultado.por_prestador.items()):
            lineas.append(f"  {total:4d}  {prestador}")

    lineas += ["", "Advertencias:"]
    if resultado.sin_prestador:
        lineas.append(
            f"  - {resultado.sin_prestador} ficha(s) sin prestador identificado, "
            "reunidas en la carpeta SIN PRESTADOR"
        )
    if resultado.sin_clasificar:
        lineas.append(
            f"  - {resultado.sin_clasificar} documento(s) sin clasificar; "
            "revisar el texto OCR o agregarlos a mano"
        )
    if resultado.compartidas:
        lineas.append(
            f"  - {len(resultado.compartidas)} hoja(s) contienen mas de un documento: "
            "la hoja se repite en cada PDF porque cada documento lleva su encabezado"
        )
    for faltante in resultado.faltantes:
        lineas.append(f"  - no se encontro el archivo original: {faltante}")
    if not any(
        [
            resultado.sin_prestador,
            resultado.sin_clasificar,
            resultado.compartidas,
            resultado.faltantes,
        ]
    ):
        lineas.append("  - sin advertencias")

    lineas += [
        "",
        "Reglas de individualizacion aplicadas:",
        "  bonos         nombre del instrumento, emisor, folio, paciente y receptor",
        "  boletas       tipo, razon social, RUT, detalle de la compra y valor",
        "  fichas        nombre del documento, prestador y fecha de atencion",
        "  recetas       paciente, fecha y prestador que firma",
        "  certificados  emisor y fecha",
        "",
        "El medicamento de las recetas esta manuscrito y no se transcribe.",
        "Los nombres manuscritos ilegibles quedan marcados para revision.",
    ]
    path.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return path
