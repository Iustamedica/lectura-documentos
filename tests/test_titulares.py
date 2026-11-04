"""Pruebas del filtro de titulares sin respaldo.

Un RUT o un nombre que aparece en un solo documento suele ser un profesional, un
acompanante o basura de OCR. En un informe para juicio no puede convertirse en
titular sin respaldo: se descarta y se reporta como advertencia para que el
abogado lo revise.
"""

from documental.models import CONF_ALTA, CONF_FALTA, Document, Field
from documental.titulares import (
    MIN_DOCUMENTOS_POR_TITULAR,
    TitularConfig,
    analizar_titulares,
    build_titulares,
    resolve_expediente,
)


def _doc(index: int, nombre: str | None = None, rut: str | None = None) -> Document:
    doc = Document(doc_id=f"d{index}", source_file="f.pdf", page=index, index_in_page=1)
    doc.familia = "bono_fonasa"
    doc.titular_nombre = Field(nombre, CONF_ALTA if nombre else CONF_FALTA, nombre)
    doc.titular_rut = Field(rut, CONF_ALTA if rut else CONF_FALTA, rut)
    return doc


class TestTitularesSinRespaldo:
    def test_el_minimo_por_defecto_es_dos_documentos(self):
        assert MIN_DOCUMENTOS_POR_TITULAR == 2

    def test_rut_visto_una_sola_vez_y_fuera_del_caso_no_es_titular(self):
        docs = [
            _doc(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5"),
            _doc(2, None, "22.222.222-2"),
        ]
        analisis = analizar_titulares(docs, [])
        assert [t.rut for t in analisis.titulares] == ["12.345.678-5"]
        assert [(t.rut, n) for t, n in analisis.descartados] == [("22.222.222-2", 1)]

    def test_rut_sin_nombre_no_es_titular_aunque_se_repita(self):
        # Talonario de bonos con pacientes distintos o el RUT del prestador
        # repetido: sin nombre no se puede afirmar a quien pertenece.
        docs = [_doc(1, None, "44.444.444-4"), _doc(2, None, "44.444.444-4")]
        analisis = analizar_titulares(docs, [])
        assert analisis.titulares == []
        assert [(t.rut, n) for t, n in analisis.descartados] == [("44.444.444-4", 2)]

    def test_rut_con_nombre_se_acepta_aunque_aparezca_una_sola_vez(self):
        docs = [_doc(1, "PEDRO SOTO PEREZ", "11.222.333-4")]
        analisis = analizar_titulares(docs, [])
        assert [t.rut for t in analisis.titulares] == ["11.222.333-4"]
        assert analisis.descartados == []

    def test_rut_declarado_en_el_caso_se_acepta_con_un_solo_documento(self):
        docs = [_doc(1, None, "33.333.333-3")]
        config = [
            TitularConfig(rut="33.333.333-3", nombre="PERSONA DECLARADA", relacion="hijo")
        ]
        analisis = analizar_titulares(docs, config)
        assert len(analisis.titulares) == 1
        assert analisis.titulares[0].nombre == "PERSONA DECLARADA"
        assert analisis.descartados == []

    def test_nombre_que_sobra_por_ocr_no_se_informa_como_titular(self):
        # El OCR agrego una palabra al final del nombre: no es otra persona.
        docs = [
            _doc(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5"),
            _doc(2, "GLORIA ESTER SOTO PEREZ RUIZ", None),
        ]
        analisis = analizar_titulares(docs, [])
        assert len(analisis.titulares) == 1
        assert [t.nombre for t, _ in analisis.descartados] == [
            "GLORIA ESTER SOTO PEREZ RUIZ"
        ]

    def test_nombre_en_orden_distinto_repetido_si_es_titular(self):
        docs = [_doc(1, "PEDRO SOTO PEREZ", None), _doc(2, "SOTO PEREZ PEDRO", None)]
        analisis = analizar_titulares(docs, [])
        assert len(analisis.titulares) == 1
        assert analisis.descartados == []

    def test_el_umbral_se_puede_bajar_para_revision_manual(self):
        docs = [_doc(1, "PEDRO SOTO PEREZ", None)]
        assert build_titulares(docs, [], min_documentos=1)[0].nombre == "PEDRO SOTO PEREZ"

    def test_los_descartados_quedan_como_advertencia_del_expediente(self):
        docs = [
            _doc(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5"),
            _doc(2, None, "22.222.222-2"),
        ]
        expediente = resolve_expediente(docs, "carpeta", "2026-11-04")
        assert [t.rut for t in expediente.titulares] == ["12.345.678-5"]
        assert any(
            "22.222.222-2" in aviso and "no se incluyo como titular" in aviso
            for aviso in expediente.advertencias
        )
