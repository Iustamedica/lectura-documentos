"""Pruebas de la ficha bibliografica del modo biblioteca."""

from __future__ import annotations

import json

import pymupdf

from documental import biblioteca


def _pdf_doctrina(path):
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 80), "La responsabilidad civil medica", fontsize=22)
    page.insert_text((72, 130), "Carlos Pizarro Wilson", fontsize=12)
    page.insert_text((72, 160), "Revista de Derecho", fontsize=10)
    page.insert_text(
        (72, 190), "DOI 10.4067/S0718-09502023000100069", fontsize=10
    )
    page2 = doc.new_page()
    page2.insert_text((72, 80), "Primera edicion: agosto 2019", fontsize=10)
    page2.insert_text((72, 110), "ISBN 978-956-14-1234-7", fontsize=10)
    doc.save(str(path))
    doc.close()
    return path


def test_isbn_valido_verifica_checksum():
    assert biblioteca._isbn_valido("9789561412347")
    assert not biblioteca._isbn_valido("9789561412345")
    assert biblioteca._isbn_valido("0306406152")


def test_ficha_extrae_titulo_autor_anio_doi_isbn(tmp_path):
    pdf = _pdf_doctrina(tmp_path / "articulo.pdf")
    ficha = biblioteca.ficha_de(pdf)
    assert "responsabilidad civil" in ficha.titulo.lower()
    assert any("Pizarro" in autor for autor in ficha.autores)
    assert ficha.anio == 2019
    assert ficha.doi == "10.4067/S0718-09502023000100069"
    assert ficha.isbn == "9789561412347"
    assert ficha.tipo == "articulo"
    assert ficha.idioma == "es"
    assert ficha.paginas == 2
    assert ficha.confianza_titulo == "alta"


def test_ficha_sin_texto_marca_nota(tmp_path):
    doc = pymupdf.open()
    doc.new_page()
    ruta = tmp_path / "vacio.pdf"
    doc.save(str(ruta))
    doc.close()
    ficha = biblioteca.ficha_de(ruta)
    assert "OCR" in ficha.notas


def test_catalogo_recursivo_y_csv_json(tmp_path):
    carpeta = tmp_path / "doctrina"
    (carpeta / "articulos").mkdir(parents=True)
    _pdf_doctrina(carpeta / "articulos" / "articulo.pdf")
    fichas = biblioteca.catalogo(carpeta)
    assert len(fichas) == 1

    csv_path = biblioteca.escribir_catalogo(
        fichas, tmp_path / "catalogo.csv", tmp_path / "catalogo.json"
    )
    contenido = csv_path.read_text(encoding="utf-8-sig")
    assert "titulo" in contenido.splitlines()[0]
    assert "Pizarro" in contenido
    datos = json.loads((tmp_path / "catalogo.json").read_text(encoding="utf-8"))
    assert datos["total"] == 1
    assert datos["fichas"][0]["anio"] == 2019


def test_catalogo_ignora_pdfs_ya_ordenados(tmp_path):
    carpeta = tmp_path / "doctrina"
    carpeta.mkdir()
    _pdf_doctrina(carpeta / "articulo.pdf")
    _pdf_doctrina(carpeta / "articulo-ordenado.pdf")
    assert len(biblioteca.catalogo(carpeta)) == 1


def test_ficha_reordenar_escribe_pdf_nuevo(tmp_path):
    origen = tmp_path / "desordenado.pdf"
    doc = pymupdf.open()
    for texto in ("3\nC", "1\nA", "2\nB"):
        page = doc.new_page()
        page.insert_text((72, 72), texto, fontsize=11)
    doc.save(str(origen))
    doc.close()

    salida = tmp_path / "salida"
    ficha = biblioteca.ficha_de(origen, reordenar=True, salida=salida)
    assert ficha.reordenado
    assert (salida / "desordenado-ordenado.pdf").exists()
    assert origen.exists()
