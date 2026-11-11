"""Pruebas de la naturaleza de la fuente (v0.6)."""

from __future__ import annotations

from documental.models import Document
from documental.perfiles import get_perfil
from documental.perfiles.legal import catalogo, naturaleza


def _doc(texto: str, clave: str = naturaleza.DOCUMENTO) -> Document:
    return Document(
        doc_id="prueba-1",
        source_file="prueba.pdf",
        page=1,
        index_in_page=1,
        familia="documento",
        naturaleza=clave,
        texto_ocr=texto,
    )


def test_boleta_es_documento():
    r = naturaleza.clasificar("BOLETA ELECTRONICA N 123 GIRO IVA TOTAL A PAGAR")
    assert r.familia == naturaleza.DOCUMENTO


def test_contrato_es_documento():
    r = naturaleza.clasificar(
        "CONTRATO DE ARRIENDO. Comparecen arrendador y arrendatario. Clausula primera."
    )
    assert r.familia == naturaleza.DOCUMENTO


def test_libro_con_isbn_es_doctrina():
    r = naturaleza.clasificar(
        "ISBN 978-956-14-1234-5. Primera edicion, agosto 2017. Editorial Juridica."
    )
    assert r.familia == naturaleza.DOCTRINA
    assert r.confianza == "alta"


def test_articulo_con_doi_es_doctrina_aunque_cite_fallos():
    r = naturaleza.clasificar(
        "DOI 10.4067/S0718-09502023000100069. Revista de Derecho. Abstract. "
        "La Corte Suprema en el considerando quinto senalo que se confirma la sentencia."
    )
    assert r.familia == naturaleza.DOCTRINA


def test_tesis_es_doctrina():
    r = naturaleza.clasificar(
        "PONTIFICIA UNIVERSIDAD CATOLICA. FACULTAD DE DERECHO. "
        "Tesis para optar al grado de Doctor en Derecho."
    )
    assert r.familia == naturaleza.DOCTRINA


def test_sentencia_de_corte_suprema_es_jurisprudencia():
    r = naturaleza.clasificar(
        "CORTE SUPREMA. Considerando primero: se confirma la sentencia apelada."
    )
    assert r.familia == naturaleza.JURISPRUDENCIA


def test_sentencia_dentro_de_expediente_es_expediente():
    r = naturaleza.clasificar(
        "EN LO PRINCIPAL: DEMANDA. ROL C-1234-2025. TRIBUNAL: 1 Juzgado Civil. "
        "Caratula: PEREZ CON BANCO. Fojas 12."
    )
    assert r.familia == naturaleza.EXPEDIENTE


def test_apelacion_es_expediente():
    r = naturaleza.clasificar(
        "EN LO PRINCIPAL: RECURSO DE APELACION. ROL 123-2025. Corte de Apelaciones."
    )
    assert r.familia == naturaleza.EXPEDIENTE


def test_resolucion_exenta_es_resolucion():
    r = naturaleza.clasificar(
        "RESOLUCION EXENTA N 123. VISTOS: Resuelvo aprobar el procedimiento."
    )
    assert r.familia == naturaleza.RESOLUCION


def test_dictamen_de_contraloria_es_resolucion():
    r = naturaleza.clasificar(
        "CONTRALORIA GENERAL DE LA REPUBLICA. Dictamen N 45.123. Vistos y resuelvo."
    )
    assert r.familia == naturaleza.RESOLUCION


def test_sumario_administrativo_es_resolucion():
    r = naturaleza.clasificar(
        "SUMARIO ADMINISTRATIVO. Investigacion sumaria. Sancion de multa."
    )
    assert r.familia == naturaleza.RESOLUCION


def test_documento_sin_texto_es_documento_baja():
    r = naturaleza.clasificar("")
    assert r.familia == naturaleza.DOCUMENTO
    assert r.confianza == "baja"


def test_tipo_canonico_de_doctrina():
    perfil = get_perfil("legal")
    assert perfil.tipo_canonico(_doc("ISBN 978-956-14-1234-5\nDERECHO CIVIL\nTOMO I", naturaleza.DOCTRINA)) == catalogo.T_DOCTRINA_LIBRO
    assert perfil.tipo_canonico(_doc("DOI 10.1234/abc\nRevista de Derecho\nResumen", naturaleza.DOCTRINA)) == catalogo.T_DOCTRINA_ARTICULO
    assert perfil.tipo_canonico(_doc("TESIS PARA OPTAR AL GRADO DE LICENCIADO", naturaleza.DOCTRINA)) == catalogo.T_DOCTRINA_TESIS
    assert perfil.tipo_canonico(_doc("CAPITULO DE LIBRO\nSUMARIO", naturaleza.DOCTRINA)) == catalogo.T_DOCTRINA_CAPITULO


def test_tipo_canonico_de_jurisprudencia_y_resoluciones():
    perfil = get_perfil("legal")
    assert perfil.tipo_canonico(_doc("CORTE SUPREMA\nSENTENCIA", naturaleza.JURISPRUDENCIA)) == catalogo.T_JURISPRUDENCIA_CS
    assert perfil.tipo_canonico(_doc("CORTE DE APELACIONES\nSENTENCIA", naturaleza.JURISPRUDENCIA)) == catalogo.T_JURISPRUDENCIA_CA
    assert perfil.tipo_canonico(_doc("TRIBUNAL CONSTITUCIONAL\nSENTENCIA", naturaleza.JURISPRUDENCIA)) == catalogo.T_JURISPRUDENCIA_TC
    assert perfil.tipo_canonico(_doc("RESOLUCION EXENTA N 1\nVISTOS\nRESUELVO", naturaleza.RESOLUCION)) == catalogo.T_RESOLUCION_ADMIN
    assert perfil.tipo_canonico(_doc("DICTAMEN N 1\nCONTRALORIA", naturaleza.RESOLUCION)) == catalogo.T_DICTAMEN
    assert perfil.tipo_canonico(_doc("SUMARIO ADMINISTRATIVO", naturaleza.RESOLUCION)) == catalogo.T_SUMARIO


def test_arbol_de_carpetas_por_fuente():
    perfil = get_perfil("legal")
    assert perfil.carpeta(catalogo.CAT_ESCRITOS) == "01-expedientes/01-escritos"
    assert perfil.carpeta(catalogo.CAT_JURISPRUDENCIA) == "02-jurisprudencia"
    assert perfil.carpeta(catalogo.CAT_RESOLUCIONES_ADMIN) == "03-resoluciones-administrativas"
    assert perfil.carpeta(catalogo.CAT_DOCTRINA) == "04-doctrina"
    assert perfil.carpeta(catalogo.CAT_CONTRATOS) == "05-documentos/01-contratos"
    assert catalogo.categoria_de_tipo(catalogo.T_DOCTRINA_LIBRO) == catalogo.CAT_DOCTRINA
    assert catalogo.categoria_de_tipo(catalogo.T_JURISPRUDENCIA_CS) == catalogo.CAT_JURISPRUDENCIA
    assert catalogo.categoria_de_tipo(catalogo.T_SUMARIO) == catalogo.CAT_RESOLUCIONES_ADMIN


def test_doctrina_no_exige_campos_criticos():
    assert catalogo.criticos_para_tipo(catalogo.T_DOCTRINA_LIBRO) == ()
    assert "rol" not in catalogo.criticos_para_tipo(catalogo.T_JURISPRUDENCIA_CS)


def test_serializacion_conserva_la_naturaleza():
    doc = _doc("texto", naturaleza.JURISPRUDENCIA)
    doc.naturaleza_confianza = "media"
    data = doc.to_dict()
    assert data["naturaleza"] == naturaleza.JURISPRUDENCIA
    recuperado = Document.from_dict(data)
    assert recuperado.naturaleza == naturaleza.JURISPRUDENCIA
    assert recuperado.naturaleza_confianza == "media"
