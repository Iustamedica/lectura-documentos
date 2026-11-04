"""Pruebas de la compilacion del PDF unico con encabezado estampado.

Los PDF de origen son sinteticos (paginas con una linea de texto): lo que se
verifica es la estructura del PDF resultante, no el contenido de los escaneos.
"""

import hashlib
from datetime import date
from pathlib import Path

import pymupdf

from documental.compilar import HEADER_HEIGHT, compilar
from documental.individualizacion import agrupar
from documental.models import CONF_ALTA, Document, Field

ANCHO = 400.0
ALTO = 600.0


def _pdf(path: Path, paginas: int = 1, texto: str = "CONTRATO") -> Path:
    doc = pymupdf.open()
    try:
        for numero in range(1, paginas + 1):
            pagina = doc.new_page(width=ANCHO, height=ALTO)
            pagina.insert_text((40, 80), f"{texto} pagina {numero}", fontsize=12)
        doc.save(str(path))
    finally:
        doc.close()
    return path


def _doc(
    page: int,
    archivo: str,
    *,
    fecha: date | None = None,
    folio: str | None = None,
    index: int = 1,
):
    doc = Document(
        doc_id=f"{archivo}-p{page}-{index}",
        source_file=archivo,
        page=page,
        index_in_page=index,
        familia="bono_fonasa",
    )
    doc.tipo_documento = Field("Bono de atencion FONASA", CONF_ALTA, "")
    doc.titular_nombre = Field("GLORIA ESTER SOTO PEREZ", CONF_ALTA, "")
    doc.titular_rut = Field("12.345.678-5", CONF_ALTA, "")
    doc.emisor_nombre = Field("HOSPITAL DE EJEMPLO", CONF_ALTA, "")
    if fecha:
        doc.fecha_emision = Field(fecha, CONF_ALTA, "")
    if folio:
        doc.folio = Field(folio, CONF_ALTA, "")
    return doc


def _hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TestCompilacion:
    def test_junta_todos_los_documentos_en_un_pdf(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        _pdf(tmp_path / "b.pdf")
        grupos = agrupar(
            [
                _doc(1, "a.pdf", fecha=date(2026, 1, 15)),
                _doc(1, "b.pdf", fecha=date(2026, 3, 12)),
            ]
        )
        resultado = compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        assert resultado.documentos == 2
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert doc.page_count == 2

    def test_estampa_el_encabezado_sobre_la_primera_hoja(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar([_doc(1, "a.pdf", fecha=date(2026, 3, 12))])
        compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            texto = doc[0].get_text()
            assert "DOCUMENTO N 1" in texto
            assert "GLORIA ESTER SOTO PEREZ" in texto
            assert "12.345.678-5" in texto
            assert "12-03-2026" in texto

    def test_el_encabezado_amplia_la_pagina_sin_tapar_contenido(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar([_doc(1, "a.pdf", fecha=date(2026, 3, 12))])
        compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert round(doc[0].rect.height) == round(ALTO + HEADER_HEIGHT)
            # El contenido original sigue presente: no se tapo con el encabezado.
            assert "CONTRATO pagina 1" in doc[0].get_text()

    def test_el_encabezado_va_solo_en_la_primera_hoja_del_grupo(self, tmp_path):
        _pdf(tmp_path / "a.pdf", paginas=3, texto="INFORME")
        grupos = agrupar(
            [_doc(1, "a.pdf", folio="77"), _doc(2, "a.pdf", folio="77"),
             _doc(3, "a.pdf", folio="77")]
        )
        assert len(grupos) == 1
        compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert doc.page_count == 3
            assert round(doc[0].rect.height) == round(ALTO + HEADER_HEIGHT)
            assert round(doc[1].rect.height) == round(ALTO)
            assert round(doc[2].rect.height) == round(ALTO)

    def test_sin_estampar_no_agrega_franja(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar([_doc(1, "a.pdf")])
        compilar(
            grupos, origen=tmp_path, destino=tmp_path / "unico.pdf", estampar=False
        )
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert round(doc[0].rect.height) == round(ALTO)

    def test_deja_marcadores_por_documento(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        _pdf(tmp_path / "b.pdf")
        grupos = agrupar(
            [
                _doc(1, "a.pdf", fecha=date(2026, 1, 15)),
                _doc(1, "b.pdf", fecha=date(2026, 3, 12)),
            ]
        )
        compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            indice = doc.get_toc()
            assert len(indice) == 2
            assert "DOC-01" in indice[0][1]
            assert indice[0][2] == 1
            assert indice[1][2] == 2


class TestSalvaguardas:
    def test_dry_run_no_escribe_el_pdf(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar([_doc(1, "a.pdf")])
        resultado = compilar(
            grupos, origen=tmp_path, destino=tmp_path / "unico.pdf", dry_run=True
        )
        assert resultado.dry_run
        assert resultado.documentos == 1
        assert not (tmp_path / "unico.pdf").exists()

    def test_avisa_los_archivos_que_faltan_sin_abortar(self, tmp_path):
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar([_doc(1, "a.pdf"), _doc(1, "no-existe.pdf")])
        resultado = compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        assert resultado.faltantes == ["no-existe.pdf"]
        assert resultado.documentos == 1
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert doc.page_count == 1

    def test_no_modifica_los_originales(self, tmp_path):
        origen = _pdf(tmp_path / "a.pdf")
        antes = _hash(origen)
        grupos = agrupar([_doc(1, "a.pdf")])
        compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        assert _hash(origen) == antes

    def test_acepta_una_imagen_como_origen(self, tmp_path):
        from PIL import Image

        Image.new("RGB", (1000, 1400), (250, 250, 250)).save(tmp_path / "foto.jpg")
        grupos = agrupar([_doc(1, "foto.jpg")])
        resultado = compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        assert resultado.documentos == 1
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert doc.page_count == 1
            assert round(doc[0].rect.height) == round(1400 * 72 / 300 + HEADER_HEIGHT)

    def test_avisa_las_hojas_con_mas_de_un_documento(self, tmp_path):
        # Una hoja con dos documentos se repite en el PDF: cada uno necesita su
        # propio encabezado. Se avisa para que el abogado lo sepa.
        _pdf(tmp_path / "a.pdf")
        grupos = agrupar(
            [_doc(1, "a.pdf", index=1, folio="111"), _doc(1, "a.pdf", index=2, folio="222")]
        )
        assert len(grupos) == 2
        resultado = compilar(grupos, origen=tmp_path, destino=tmp_path / "unico.pdf")
        assert resultado.paginas_compartidas == ["a.pdf p.1"]
        with pymupdf.open(str(tmp_path / "unico.pdf")) as doc:
            assert doc.page_count == 2

    def test_acepta_varias_carpetas_de_origen(self, tmp_path):
        primera = tmp_path / "uno"
        segunda = tmp_path / "dos"
        primera.mkdir()
        segunda.mkdir()
        _pdf(primera / "a.pdf")
        _pdf(segunda / "b.pdf")
        grupos = agrupar([_doc(1, "a.pdf"), _doc(1, "b.pdf")])
        resultado = compilar(
            grupos, origen=[primera, segunda], destino=tmp_path / "unico.pdf"
        )
        assert resultado.documentos == 2
        assert resultado.faltantes == []
