"""Pruebas de la clasificacion rapida SIN OCR (capa de texto de los PDF)."""

from pathlib import Path

import pymupdf

from documental.sinocr import clasificar_sin_ocr, resumen


def _pdf_con_texto(path: Path, texto: str) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), texto)
    doc.save(str(path))
    doc.close()


def test_clasifica_pdf_con_texto(tmp_path: Path):
    _pdf_con_texto(tmp_path / "a.pdf", "CERTIFICADO DE NACIMIENTO Circunscripcion Santiago")
    items = clasificar_sin_ocr(tmp_path)
    it = next(i for i in items if i.archivo.endswith("a.pdf"))
    assert it.tiene_texto is True
    assert "Certificado de nacimiento" in it.tipo


def test_imagen_requiere_ocr(tmp_path: Path):
    (tmp_path / "b.jpg").write_bytes(b"\xff\xd8\xff\xd9\x00\x00\x00")
    items = clasificar_sin_ocr(tmp_path)
    it = next(i for i in items if i.archivo.endswith("b.jpg"))
    assert it.tiene_texto is False
    assert "requiere OCR" in it.tipo


def test_resumen_cuenta_categorias(tmp_path: Path):
    _pdf_con_texto(tmp_path / "a.pdf", "CERTIFICADO DE NACIMIENTO Circunscripcion Santiago")
    (tmp_path / "b.jpg").write_bytes(b"\xff\xd8\xff\xd9\x00\x00\x00")
    r = resumen(clasificar_sin_ocr(tmp_path))
    assert r["total"] == 2
    assert r["con_texto"] == 1
    assert r["requiere_ocr"] == 1
