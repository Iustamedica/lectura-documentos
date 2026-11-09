"""Pruebas de la fusion de bloques de una misma hoja."""

from documental.individualizacion import consolidar_documentos
from documental.models import Document


def _bloque(page: int, index: int, texto: str, **campos) -> Document:
    doc = Document(
        doc_id=f"x-{page}-{index}", source_file="a.pdf", page=page,
        index_in_page=index, familia="documento_clinico", texto_ocr=texto,
    )
    for nombre, valor in campos.items():
        getattr(doc, nombre).value = valor
    return doc


def test_consolida_bloques_de_misma_hoja():
    d1 = _bloque(1, 1, "EPICRISIS CLINICA ALEMANA\nPaciente: CAMILA HUERTA")
    d2 = _bloque(1, 2, "continuacion sin datos utiles")
    merged = consolidar_documentos([d1, d2])
    assert len(merged) == 1
    assert "continuacion" in merged[0].texto_ocr


def test_no_consolida_dos_bonos_distintos():
    d1 = _bloque(1, 1, "BONO DE ATENCION AMBULATORIA FONASA", folio="111")
    d2 = _bloque(1, 2, "BONO DE ATENCION AMBULATORIA FONASA", folio="222")
    assert len(consolidar_documentos([d1, d2])) == 2
