"""Pruebas de la preparacion de fotos: JPG -> PDF sin perder resolucion.

Todo se hace con imagenes sinteticas de color plano: lo que se verifica es el
tamano de pagina, la agrupacion por momento de captura y que los originales no
se toquen, no el contenido de la imagen.
"""

import hashlib
from datetime import datetime
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from documental.ingesta import (
    DPI_CONVERSION,
    agrupar_por_tiempo,
    imagen_a_pdf,
    marca_de_tiempo,
    preparar,
)


def _imagen(path: Path, tamano=(1200, 1600)) -> Path:
    Image.new("RGB", tamano, (250, 250, 250)).save(path)
    return path


def _hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TestMarcaDeTiempo:
    def test_se_lee_del_nombre_de_la_camara(self, tmp_path):
        foto = _imagen(tmp_path / "IMG_20261102_145929.jpg")
        assert marca_de_tiempo(foto) == datetime(2026, 11, 2, 14, 59, 29)

    def test_sin_marca_en_el_nombre_usa_la_fecha_del_archivo(self, tmp_path):
        foto = _imagen(tmp_path / "foto.jpg")
        assert marca_de_tiempo(foto) is not None


class TestAgrupacionPorTiempo:
    def test_agrupa_fotos_tomadas_con_segundos_de_diferencia(self):
        items = [
            (Path("a.jpg"), datetime(2026, 11, 2, 14, 59, 29)),
            (Path("b.jpg"), datetime(2026, 11, 2, 14, 59, 37)),
            (Path("c.jpg"), datetime(2026, 11, 2, 15, 5, 0)),
        ]
        grupos = agrupar_por_tiempo(items, 30)
        assert [len(grupo) for grupo in grupos] == [2, 1]

    def test_segundos_en_cero_desactiva_la_agrupacion(self):
        items = [
            (Path("a.jpg"), datetime(2026, 11, 2, 14, 59, 29)),
            (Path("b.jpg"), datetime(2026, 11, 2, 14, 59, 30)),
        ]
        assert len(agrupar_por_tiempo(items, 0)) == 2

    def test_una_foto_sin_momento_no_se_agrupa(self):
        # Sin dato de tiempo no hay base para suponer que son el mismo documento.
        items = [(Path("a.jpg"), None), (Path("b.jpg"), None)]
        assert len(agrupar_por_tiempo(items, 30)) == 2


class TestImagenAPdf:
    def test_una_pagina_por_imagen(self, tmp_path):
        fotos = [_imagen(tmp_path / f"f{i}.jpg") for i in range(3)]
        pdf = imagen_a_pdf(fotos, tmp_path / "salida.pdf")
        with pymupdf.open(str(pdf)) as doc:
            assert doc.page_count == 3

    def test_no_reduce_la_resolucion(self, tmp_path):
        # 1200 x 1600 px a 300 dpi son 288 x 384 puntos: al renderizar de nuevo
        # a 300 dpi se recuperan los mismos pixeles.
        foto = _imagen(tmp_path / "grande.jpg", (1200, 1600))
        pdf = imagen_a_pdf([foto], tmp_path / "salida.pdf")
        with pymupdf.open(str(pdf)) as doc:
            rect = doc[0].rect
            assert round(rect.width) == round(1200 * 72 / DPI_CONVERSION)
            assert round(rect.height) == round(1600 * 72 / DPI_CONVERSION)

    def test_varias_imagenes_en_un_solo_pdf(self, tmp_path):
        fotos = [_imagen(tmp_path / f"f{i}.jpg") for i in range(2)]
        pdf = imagen_a_pdf(fotos, tmp_path / "grupo.pdf")
        with pymupdf.open(str(pdf)) as doc:
            assert doc.page_count == 2


class TestPreparar:
    def test_convierte_cada_foto_en_un_pdf(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        for i in range(3):
            _imagen(origen / f"IMG_20261102_14592{i}.jpg")
        resultado = preparar(origen, tmp_path / "pdf", copiar_pdf=False)
        assert resultado.total_imagenes == 3
        assert len(list((tmp_path / "pdf").glob("*.pdf"))) == 3

    def test_agrupa_las_fotos_del_mismo_documento(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        _imagen(origen / "IMG_20261102_145929.jpg")
        _imagen(origen / "IMG_20261102_145937.jpg")
        _imagen(origen / "IMG_20261102_150500.jpg")
        resultado = preparar(
            origen, tmp_path / "pdf", unir_por_tiempo=30, copiar_pdf=False
        )
        assert [len(grupo) for grupo in resultado.grupos] == [2, 1]
        assert len(list((tmp_path / "pdf").glob("*.pdf"))) == 2

    def test_copia_los_pdf_que_ya_existian(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        with pymupdf.open() as doc:
            doc.new_page()
            doc.save(str(origen / "escaneo.pdf"))
        resultado = preparar(origen, tmp_path / "pdf")
        assert len(resultado.pdfs_copiados) == 1
        assert (tmp_path / "pdf" / "escaneo.pdf").exists()

    def test_dry_run_no_escribe_nada(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        _imagen(origen / "IMG_20261102_145929.jpg")
        resultado = preparar(origen, tmp_path / "pdf", dry_run=True)
        assert resultado.dry_run
        assert resultado.total_imagenes == 1
        assert not (tmp_path / "pdf").exists()

    def test_no_toca_los_originales(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        foto = _imagen(origen / "IMG_20261102_145929.jpg")
        antes = _hash(foto)
        preparar(origen, tmp_path / "pdf")
        assert _hash(foto) == antes

    def test_rechaza_un_destino_que_ya_tiene_archivos(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        _imagen(origen / "IMG_20261102_145929.jpg")
        destino = tmp_path / "pdf"
        destino.mkdir()
        (destino / "previo.pdf").write_bytes(b"%PDF-1.4\n")
        with pytest.raises(FileExistsError):
            preparar(origen, destino)

    def test_el_mapa_deja_trazabilidad(self, tmp_path):
        origen = tmp_path / "fotos"
        origen.mkdir()
        _imagen(origen / "IMG_20261102_145929.jpg")
        resultado = preparar(origen, tmp_path / "pdf", copiar_pdf=False)
        mapa = resultado.escribir_mapa(tmp_path / "mapa.csv")
        texto = mapa.read_text(encoding="utf-8-sig")
        assert "imagen_original" in texto
        assert "IMG_20261102_145929.jpg" in texto
