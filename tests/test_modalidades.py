"""Pruebas de las cuatro modalidades documentales (v0.8)."""

from __future__ import annotations

from documental.models import Document
from documental.perfiles import get_perfil, modalidad_de_carpeta
from documental.perfiles.legal import catalogo as legal_catalogo


def _doc(texto: str, source: str = "x.pdf") -> Document:
    return Document(
        doc_id="x",
        source_file=source,
        page=1,
        index_in_page=1,
        texto_ocr=texto,
    )


def test_modalidades_registradas_y_alias():
    assert get_perfil().nombre == "judicial"
    assert get_perfil("legal").nombre == "judicial"
    assert get_perfil("sentencias").nombre == "jurisprudencia"
    assert get_perfil("actos").nombre == "administrativo"
    assert get_perfil("biblioteca").nombre == "doctrina"
    # Una configuracion antigua de salud no debe romper la app.
    assert get_perfil("salud").nombre == "judicial"


def test_modalidad_por_nombre_de_carpeta(tmp_path):
    doctrina = tmp_path / "Doctrina" / "articulos"
    doctrina.mkdir(parents=True)
    assert modalidad_de_carpeta(doctrina) == "doctrina"

    juris = tmp_path / "Jurisprudencia" / "Corte Suprema"
    juris.mkdir(parents=True)
    assert modalidad_de_carpeta(juris) == "jurisprudencia"

    actos = tmp_path / "Actos administrativos" / "Contraloria"
    actos.mkdir(parents=True)
    assert modalidad_de_carpeta(actos) == "administrativo"

    judicial = tmp_path / "Expediente" / "escritos"
    judicial.mkdir(parents=True)
    assert modalidad_de_carpeta(judicial) == "judicial"


def test_doctrina_conserva_el_pdf_y_no_exige_criticos():
    perfil = get_perfil("doctrina")
    assert perfil.un_documento_por_pdf is True
    assert perfil.paginas_muestra_ocr == 0
    assert perfil.criticos_de(_doc("")) == ()

    doc = _doc("DERECHO CIVIL\nISBN 978-956-123-456-7\nPrimera edicion 2019")
    perfil.refinar(doc)
    assert doc.extra["isbn"].value.startswith("978")
    assert perfil.tipo_canonico(doc) == "Libro"
    assert perfil.categoria_de_tipo(perfil.tipo_canonico(doc)) == "libros"


def test_jurisprudencia_extrae_rol_tribunal_fecha_y_resultado():
    perfil = get_perfil("jurisprudencia")
    doc = _doc(
        "CORTE SUPREMA\nSantiago, 12 de marzo de 2024\nROL 1234-2024\n"
        "Sala Primera\nCaratula: Perez con Fisco\nSe confirma la sentencia"
    )
    perfil.refinar(doc)

    assert doc.extra["rol"].value == "1234-2024"
    assert doc.extra["tribunal"].value == "Corte Suprema"
    assert doc.fecha_emision.value == "2024-03-12"
    assert doc.extra["resultado"].value == "Confirma"
    assert perfil.tipo_canonico(doc) == "Sentencia de la Corte Suprema"
    assert perfil.categoria_de_tipo(perfil.tipo_canonico(doc)) == "corte_suprema"


def test_administrativo_extrae_institucion_numero_y_fecha():
    perfil = get_perfil("administrativo")
    doc = _doc(
        "CONTRALORIA GENERAL DE LA REPUBLICA\n"
        "RESOLUCION EXENTA N° 1234\nSantiago, 27.03.2024\n"
        "MATERIA: Instrucciones sobre ausencias"
    )
    perfil.refinar(doc)

    assert doc.extra["institucion"].value == "Contraloria General de la Republica"
    assert doc.extra["numero"].value == "1234"
    assert doc.fecha_emision.value == "2024-03-27"
    assert perfil.categoria_de_tipo(perfil.tipo_canonico(doc)) == "contraloria"


def test_judicial_puede_juntar_o_separar_anexos():
    perfil = get_perfil("legal")
    assert perfil.categoria_de_tipo(legal_catalogo.T_JURISPRUDENCIA_CS) == (
        legal_catalogo.CAT_JURISPRUDENCIA
    )

    perfil.anexos_juntos = True
    try:
        assert perfil.categoria_de_tipo(legal_catalogo.T_JURISPRUDENCIA_CS) == (
            legal_catalogo.CAT_OTROS
        )
        assert perfil.categoria_de_tipo(legal_catalogo.T_DOCTRINA_LIBRO) == (
            legal_catalogo.CAT_OTROS
        )
    finally:
        perfil.anexos_juntos = False


def test_columnas_de_cada_modalidad_tienen_claves_unicas():
    for clave in ("judicial", "doctrina", "jurisprudencia", "administrativo"):
        perfil = get_perfil(clave)
        nombres = [nombre for nombre, _ in perfil.columnas()]
        assert len(nombres) == len(set(nombres))
        assert perfil.categorias[-1].clave == "otros"
