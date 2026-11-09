"""Pruebas de la extraccion de tokens desde la capa de texto (sin OCR)."""

import pymupdf

from documental.ocr import ocr_pages


def _pdf_texto(path, texto):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), texto)
    doc.save(str(path))
    doc.close()


def test_pdf_con_texto_usa_capa_texto(tmp_path):
    _pdf_texto(tmp_path / "a.pdf",
               "CERTIFICADO DE NACIMIENTO circunscripcion Santiago registro civil Republica de Chile")
    pages = ocr_pages(tmp_path / "a.pdf", dpi=150)
    assert len(pages) == 1
    assert len(pages[0].tokens) >= 8
    assert any("NACIMIENTO" in t.text.upper() for t in pages[0].tokens)


def test_pdf_en_blanco_no_rompe(tmp_path):
    """Una hoja casi vacia no debe provocar division por cero en el preprocesado."""
    doc = pymupdf.open()
    doc.new_page()
    doc.save(str(tmp_path / "vacio.pdf"))
    doc.close()
    pages = ocr_pages(tmp_path / "vacio.pdf", dpi=120)
    assert len(pages) == 1
