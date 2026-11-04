"""Pruebas de la individualizacion: agrupar hojas y numerar documentos.

Se construyen documentos con los mismos objetos que produce el pipeline (sin
OCR), para verificar la logica de agrupacion y el orden cronologico.
"""

from datetime import date

from docx import Document as DocxDocument

from documental.individualizacion import (
    agrupar,
    escribir_csv,
    escribir_docx,
    fecha_de,
    filas,
)
from documental.models import CONF_ALTA, CONF_FALTA, Document, Field


def _doc(
    page: int,
    *,
    archivo: str = "escaneo.pdf",
    familia: str = "bono_fonasa",
    folio: str | None = None,
    rut: str | None = None,
    nombre: str | None = None,
    fecha: date | None = None,
    tipo: str | None = None,
    index: int = 1,
) -> Document:
    doc = Document(
        doc_id=f"{archivo}-p{page}-{index}",
        source_file=archivo,
        page=page,
        index_in_page=index,
        familia=familia,
    )
    if folio:
        doc.folio = Field(folio, CONF_ALTA, folio)
    if rut:
        doc.titular_rut = Field(rut, CONF_ALTA, rut)
    if nombre:
        doc.titular_nombre = Field(nombre, CONF_ALTA, nombre)
    if fecha:
        doc.fecha_emision = Field(fecha, CONF_ALTA, "")
    if tipo:
        doc.tipo_documento = Field(tipo, CONF_ALTA, "")
    return doc


class TestFechaDelDocumento:
    def test_usa_la_fecha_de_emision(self):
        doc = _doc(1, fecha=date(2026, 3, 12))
        assert fecha_de(doc) == date(2026, 3, 12)

    def test_si_no_hay_emision_usa_la_atencion(self):
        doc = _doc(1)
        doc.fecha_emision = Field(None, CONF_FALTA, "")
        doc.fecha_atencion = Field(date(2026, 4, 1), CONF_ALTA, "")
        assert fecha_de(doc) == date(2026, 4, 1)

    def test_acepta_la_fecha_como_texto(self):
        doc = _doc(1)
        doc.fecha_emision = Field("12-03-2026", CONF_ALTA, "")
        assert fecha_de(doc) == date(2026, 3, 12)


class TestAgrupacion:
    def test_hojas_consecutivas_del_mismo_documento_se_unen(self):
        docs = [_doc(1, folio="123"), _doc(2, folio="123"), _doc(3, folio="123")]
        grupos = agrupar(docs)
        assert len(grupos) == 1
        assert grupos[0].paginas == [1, 2, 3]
        assert grupos[0].paginas_texto == "pp. 1-3"

    def test_folio_distinto_los_separa(self):
        docs = [_doc(1, folio="123"), _doc(2, folio="456")]
        assert len(agrupar(docs)) == 2

    def test_archivo_distinto_los_separa(self):
        docs = [_doc(1, archivo="a.pdf"), _doc(2, archivo="b.pdf")]
        assert len(agrupar(docs)) == 2

    def test_paginas_no_consecutivas_los_separa(self):
        docs = [_doc(1), _doc(3)]
        assert len(agrupar(docs)) == 2

    def test_familia_distinta_los_separa(self):
        docs = [_doc(1, familia="bono_fonasa"), _doc(2, familia="pagare")]
        assert len(agrupar(docs)) == 2

    def test_titular_distinto_los_separa(self):
        docs = [_doc(1, rut="12.345.678-5"), _doc(2, rut="11.111.111-1")]
        assert len(agrupar(docs)) == 2

    def test_documento_sin_clasificar_sin_senales_no_se_une(self):
        # Ante la duda conviene un documento de mas que uno mal unido.
        docs = [_doc(1, familia="desconocido"), _doc(2, familia="desconocido")]
        assert len(agrupar(docs)) == 2

    def test_documento_sin_clasificar_con_mismo_folio_se_une(self):
        docs = [
            _doc(1, familia="desconocido", folio="777"),
            _doc(2, familia="desconocido", folio="777"),
        ]
        assert len(agrupar(docs)) == 1


class TestNumeracion:
    def test_numera_en_orden_cronologico(self):
        docs = [
            _doc(1, archivo="a.pdf", fecha=date(2026, 5, 1)),
            _doc(1, archivo="b.pdf", fecha=date(2026, 1, 15)),
        ]
        grupos = agrupar(docs)
        assert [grupo.archivo for grupo in grupos] == ["b.pdf", "a.pdf"]
        assert [grupo.numero for grupo in grupos] == [1, 2]

    def test_los_documentos_sin_fecha_quedan_al_final(self):
        docs = [
            _doc(1, archivo="sin.pdf"),
            _doc(1, archivo="con.pdf", fecha=date(2026, 5, 1)),
        ]
        grupos = agrupar(docs)
        assert [grupo.archivo for grupo in grupos] == ["con.pdf", "sin.pdf"]

    def test_la_etiqueta_va_con_dos_digitos(self):
        grupos = agrupar([_doc(1)])
        assert grupos[0].etiqueta == "DOC-01"
        assert grupos[0].numero == 1

    def test_un_grupo_toma_el_primer_valor_no_vacio(self):
        docs = [_doc(1, folio="123"), _doc(2, folio="123", tipo="Bono FONASA")]
        grupo = agrupar(docs)[0]
        assert grupo.valor("tipo_documento") == "Bono FONASA"
        assert grupo.tipo == "Bono FONASA"

    def test_sin_tipo_usa_la_etiqueta_de_la_familia(self):
        grupos = agrupar([_doc(1, familia="pagare")])
        assert grupos[0].tipo == "Pagare"


class TestTablaDeIndividualizacion:
    def _grupos(self):
        return agrupar(
            [
                _doc(
                    1,
                    archivo="a.pdf",
                    folio="1234",
                    rut="12.345.678-5",
                    nombre="GLORIA ESTER SOTO PEREZ",
                    fecha=date(2026, 3, 12),
                    tipo="Bono de atencion FONASA",
                ),
                _doc(
                    1,
                    archivo="b.pdf",
                    folio="999",
                    rut="11.111.111-1",
                    nombre="LUIS ANDRES SOTO PEREZ",
                    fecha=date(2026, 1, 15),
                    tipo="Ticket de farmacia",
                ),
            ]
        )

    def test_una_fila_por_documento(self):
        assert len(filas(self._grupos())) == 2

    def test_la_fila_trae_lo_que_pide_el_escrito(self):
        fila = filas(self._grupos())[0]
        assert fila["N"] == "1"
        assert fila["fecha"] == "15-01-2026"
        assert fila["tipo"] == "Ticket de farmacia"
        assert fila["rut_titular"] == "11.111.111-1"
        assert fila["archivo"] == "b.pdf"

    def test_csv_una_fila_por_documento(self, tmp_path):
        path = escribir_csv(self._grupos(), tmp_path / "ind.csv")
        lineas = path.read_text(encoding="utf-8-sig").strip().splitlines()
        assert len(lineas) == 3  # encabezado + 2 documentos
        assert lineas[0].startswith("N;tipo;fecha")

    def test_word_tiene_una_fila_por_documento(self, tmp_path):
        path = escribir_docx(self._grupos(), tmp_path / "ind.docx")
        documento = DocxDocument(str(path))
        tabla = documento.tables[0]
        assert len(tabla.rows) == 3  # encabezado + 2 documentos
        assert tabla.rows[0].cells[0].text == "N"
