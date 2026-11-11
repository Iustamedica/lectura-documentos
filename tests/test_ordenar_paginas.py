"""Pruebas del ordenamiento de paginas por numero impreso."""

from __future__ import annotations

import pymupdf

from documental.ordenar_paginas import analizar, detectar_numero, ordenar_pdf


def _pdf(path, paginas):
    doc = pymupdf.open()
    for texto in paginas:
        page = doc.new_page()
        y = 72
        for linea in texto.splitlines():
            page.insert_text((72, y), linea, fontsize=11)
            y += 18
    doc.save(str(path))
    doc.close()
    return path


def _textos(path):
    with pymupdf.open(str(path)) as doc:
        return [doc[i].get_text().strip() for i in range(doc.page_count)]


def _letras(path):
    """Ultima linea de cada pagina: la letra que identifica el contenido."""
    return [texto.splitlines()[-1].strip() for texto in _textos(path)]


def test_detecta_numero_impreso():
    assert detectar_numero("849\nPUNTO DE VISTA\nTexto") == 849
    assert detectar_numero("Texto\n\n851") == 851


def test_no_confunde_anios_ni_montos():
    assert detectar_numero("2020\nRevista de Derecho") is None
    assert detectar_numero("$ 1.500\nTotal") is None


def test_reordena_paginas_desordenadas(tmp_path):
    origen = _pdf(tmp_path / "libro.pdf", ["3\nC", "1\nA", "2\nB"])
    resultado = ordenar_pdf(origen, tmp_path / "ordenado.pdf")
    assert resultado.reordenado
    assert _letras(resultado.destino) == ["A", "B", "C"]


def test_conserva_portada_sin_numero_al_inicio(tmp_path):
    origen = _pdf(
        tmp_path / "libro.pdf", ["PORTADA\nLIBRO", "3\nC", "1\nA", "2\nB"]
    )
    resultado = ordenar_pdf(origen, tmp_path / "ordenado.pdf")
    assert resultado.reordenado
    textos = _textos(resultado.destino)
    assert textos[0].startswith("PORTADA")
    assert _letras(resultado.destino)[1:] == ["A", "B", "C"]


def test_no_reordena_si_hay_numeros_repetidos(tmp_path):
    origen = _pdf(tmp_path / "libro.pdf", ["1\nA", "1\nB", "3\nC"])
    resultado = ordenar_pdf(origen, tmp_path / "ordenado.pdf")
    assert not resultado.reordenado
    assert "repetidos" in resultado.motivo
    assert resultado.destino is None


def test_reordena_numeros_romanos(tmp_path):
    origen = _pdf(tmp_path / "libro.pdf", ["ii\nB", "i\nA", "iii\nC"])
    resultado = ordenar_pdf(origen, tmp_path / "ordenado.pdf")
    assert resultado.reordenado
    assert _letras(resultado.destino) == ["A", "B", "C"]


def test_forzar_con_pagina_sin_numero(tmp_path):
    origen = _pdf(tmp_path / "libro.pdf", ["1\nA", "SIN NUMERO", "3\nC"])
    resultado = ordenar_pdf(origen, tmp_path / "ordenado.pdf", forzar=True)
    assert resultado.reordenado
    textos = _textos(resultado.destino)
    assert textos[0].startswith("1")
    assert textos[1].startswith("SIN NUMERO")
    assert textos[2].startswith("3")


def test_analizar_informa_motivo_si_falta_texto(tmp_path):
    origen = _pdf(tmp_path / "vacio.pdf", ["A", "B", "C"])
    analisis = analizar(origen)
    assert not analisis.reordenable
    assert "numero legible" in analisis.motivo
