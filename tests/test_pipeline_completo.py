"""Pruebas del tratamiento de textos completos (doctrina) en el pipeline."""

from __future__ import annotations

import pymupdf

from documental.pipeline import (
    PipelineOptions,
    doctrina_en_pdf,
    process_folder,
)
from documental.perfiles import get_perfil

DOCTRINA = (
    "La responsabilidad civil medica\n"
    "Revista de Derecho, ISSN 0718-0950\n"
    "DOI 10.4067/S0718-09502023000100069\n"
    "Resumen\n"
    "Palabras clave: responsabilidad, culpa, medicina.\n"
    "Abstract\n"
    "This article studies medical liability and the standard of care.\n"
    "Referencias bibliograficas\n"
)


def _pdf(path, paginas):
    doc = pymupdf.open()
    for texto in paginas:
        page = doc.new_page()
        y = 72
        for linea in texto.splitlines():
            page.insert_text((72, y), linea, fontsize=10)
            y += 16
    doc.save(str(path))
    doc.close()
    return path


def test_doctrina_es_un_solo_documento(tmp_path):
    _pdf(tmp_path / "2020_articulo.pdf", [DOCTRINA] * 3)
    expediente = process_folder(tmp_path, perfil="legal")
    assert len(expediente.documentos) == 1
    documento = expediente.documentos[0]
    assert documento.naturaleza == "doctrina"
    assert documento.page == 1
    assert documento.paginas == [1, 2, 3]
    assert "responsabilidad" in documento.titulo.lower()


def test_expediente_sigue_pagina_por_pagina(tmp_path):
    pagina_1 = (
        "ROL 123-2020\nEn lo principal\nDemanda de indemnizacion\n"
        "Solicito tener por interpuesta la demanda."
    )
    pagina_2 = (
        "ROL 456-2021\nEn lo principal\nContestacion\n"
        "Contesto la demanda y opongo excepciones."
    )
    _pdf(tmp_path / "expediente.pdf", [pagina_1, pagina_2])
    expediente = process_folder(tmp_path, perfil="legal")
    assert len(expediente.documentos) > 1
    assert all(doc.naturaleza != "doctrina" for doc in expediente.documentos)


def test_paginas_sobreviven_al_json(tmp_path):
    _pdf(tmp_path / "2020_articulo.pdf", [DOCTRINA] * 3)
    expediente = process_folder(tmp_path, perfil="legal")
    from documental.models import Document

    recuperado = Document.from_dict(expediente.to_dict()["documentos"][0])
    assert recuperado.paginas == [1, 2, 3]
    assert recuperado.naturaleza == "doctrina"


def test_doctrina_en_pdf_detecta_sin_ocr(tmp_path):
    ruta = _pdf(tmp_path / "2020_articulo.pdf", [DOCTRINA] * 2)
    detectado, confianza = doctrina_en_pdf(ruta, get_perfil("legal"))
    assert detectado
    assert confianza in {"alta", "media"}


def test_sin_dividir_no_hace_ocr_en_pdf_sin_texto(tmp_path):
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    ruta = tmp_path / "escaneo.pdf"
    doc.save(str(ruta))
    doc.close()

    expediente = process_folder(
        tmp_path,
        perfil="legal",
        options=PipelineOptions(un_documento_por_pdf=True),
    )
    assert len(expediente.documentos) == 1
    documento = expediente.documentos[0]
    assert documento.paginas == [1, 2, 3]
    assert not documento.texto_ocr
    assert "OCR" in documento.observaciones.value


def test_carpeta_doctrina_trata_escaneos_sin_ocr(tmp_path):
    carpeta = tmp_path / "Doctrina"
    carpeta.mkdir()
    doc = pymupdf.open()
    for _ in range(3):
        doc.new_page()
    ruta = carpeta / "libro.pdf"
    doc.save(str(ruta))
    doc.close()

    expediente = process_folder(carpeta, perfil="legal")
    assert len(expediente.documentos) == 1
    documento = expediente.documentos[0]
    assert documento.paginas == [1, 2, 3]
    assert not documento.texto_ocr


def test_refinar_no_inventa_tribunal_en_doctrina():
    from documental.models import Document

    documento = Document(
        doc_id="libro",
        source_file="libro.pdf",
        page=1,
        index_in_page=1,
        naturaleza="doctrina",
        texto_ocr="Tribunal de tesis por honrarme. ROL 123-2020",
    )
    get_perfil("legal").refinar(documento)
    assert documento.extra == {}


def test_documento_sin_campos_criticos_no_queda_faltante():
    from documental.models import Document

    documento = Document(
        doc_id="doctrina", source_file="libro.pdf", page=1, index_in_page=1
    )
    assert documento.confianza_global(()) == "alta"
    assert documento.campos_a_revisar(()) == []


def test_sin_dividir_fuerza_un_documento(tmp_path):
    pagina_1 = (
        "ROL 123-2020\nEn lo principal\nDemanda de indemnizacion\n"
        "Solicito tener por interpuesta la demanda."
    )
    pagina_2 = (
        "ROL 123-2020\nEn lo principal\nAcompano documentos\n"
        "Solicito tener presente."
    )
    _pdf(tmp_path / "expediente.pdf", [pagina_1, pagina_2])
    expediente = process_folder(
        tmp_path,
        perfil="legal",
        options=PipelineOptions(un_documento_por_pdf=True),
    )
    assert len(expediente.documentos) == 1
