"""Pruebas del perfil legal (catalogo, clasificacion, extraccion y agrupacion)."""

from __future__ import annotations

from datetime import date

from documental import categorias
from documental.cli import build_parser
from documental.individualizacion import agrupar, filas
from documental.models import Document, Expediente, Field
from documental.perfiles import get_perfil
from documental.perfiles.legal import catalogo
from documental.revisor import generar_revisor


def _doc(texto: str, familia: str = "otro", page: int = 1, index: int = 1,
         source: str = "a.pdf") -> Document:
    return Document(
        doc_id=f"{source}-p{page}-{index}",
        source_file=source,
        page=page,
        index_in_page=index,
        familia=familia,
        texto_ocr=texto,
    )


# ---------------------------------------------------------------------------
# Catalogo
# ---------------------------------------------------------------------------

def test_categorias_unicas_y_tipos_validos():
    claves = [categoria.clave for categoria in catalogo.CATEGORIAS]
    assert len(claves) == len(set(claves))
    assert claves[-1] == catalogo.CAT_OTROS
    for tipo in catalogo.TIPOS:
        assert catalogo.categoria_de_tipo(tipo) in claves


def test_perfil_legal_expone_su_catalogo():
    perfil = get_perfil("legal")
    assert perfil.nombre == "legal"
    assert perfil.clave_otros == catalogo.CAT_OTROS
    assert perfil.etiqueta(catalogo.CAT_ESCRITOS) == "Escritos"
    assert perfil.carpeta(catalogo.CAT_RESOLUCIONES) == "02-resoluciones"
    assert "rol" in perfil.campos_criticos()


def test_perfil_por_defecto_es_salud():
    assert get_perfil().nombre == "salud"


# ---------------------------------------------------------------------------
# Clasificacion y tipo canonico
# ---------------------------------------------------------------------------

def test_clasifica_resolucion_y_escrito():
    resolucion = (
        "SENTENCIA DEFINITIVA. Vistos: Considerando primero: ... Resuelvo: "
        "condeno a la demandada al pago de las costas."
    )
    escrito = (
        "EN LO PRINCIPAL: DEMANDA. S.J.L. en lo civil. Solicito tener por "
        "interpuesta la demanda en contra de Banco X."
    )
    assert get_perfil("legal").clasificar(resolucion).familia == "resolucion"
    assert get_perfil("legal").clasificar(escrito).familia == "escrito"


def test_tipos_canonicos_frecuentes():
    casos = {
        "SENTENCIA DEFINITIVA\nVistos y considerando\nResuelvo": catalogo.T_SENTENCIA,
        "EN LO PRINCIPAL: DEMANDA\nSolicito tener por interpuesta": catalogo.T_DEMANDA,
        "CEDULA DE NOTIFICACION\nCertifico que notifique": catalogo.T_CEDULA,
        "CONTRATO DE ARRIENDO\nComparecen las partes": catalogo.T_CONTRATO_ARRENDAMIENTO,
        "BOLETA ELECTRONICA\nGiro: servicios\nIVA $1.234": catalogo.T_BOLETA,
    }
    perfil = get_perfil("legal")
    for texto, esperado in casos.items():
        assert perfil.tipo_canonico(_doc(texto)) == esperado, texto


# ---------------------------------------------------------------------------
# Extraccion de datos (ROL, tribunal, partes, fecha)
# ---------------------------------------------------------------------------

TEXTO_JUDICIAL = """2 JUZGADO CIVIL DE SANTIAGO
ROL C-1234-2025
Caratula: PEREZ SOTO CON BANCO X
Parte demandante: JUAN PEREZ SOTO
Parte demandada: BANCO X S.A.
Santiago, 12 de marzo de 2025
Fojas 12
"""


def test_refinar_extrae_rol_tribunal_caratula_y_fecha():
    perfil = get_perfil("legal")
    doc = _doc(TEXTO_JUDICIAL, familia="resolucion")
    perfil.refinar(doc)

    assert doc.extra["rol"].value == "C-1234-2025"
    assert "JUZGADO CIVIL DE SANTIAGO" in doc.extra["tribunal"].value.upper()
    assert doc.extra["caratula"].value == "PEREZ SOTO CON BANCO X"
    assert doc.extra["parte_demandante"].value == "JUAN PEREZ SOTO"
    assert doc.extra["parte_demandada"].value == "BANCO X S.A."
    assert doc.extra["fojas"].value == "12"
    assert doc.fecha_emision.value == "12-03-2025"


def test_refinar_no_sobrescribe_un_dato_ya_leido():
    perfil = get_perfil("legal")
    doc = _doc(TEXTO_JUDICIAL, familia="resolucion")
    doc.extra["rol"] = type(doc.folio)()
    doc.extra["rol"].set("C-9999-2024", "alta")
    perfil.refinar(doc)
    assert doc.extra["rol"].value == "C-9999-2024"


# ---------------------------------------------------------------------------
# Agrupacion (individualizacion)
# ---------------------------------------------------------------------------

def test_no_une_documentos_con_rol_distinto():
    perfil = get_perfil("legal")
    docs = [
        _doc("SENTENCIA DEFINITIVA\nROL C-111-2025", page=1),
        _doc("SENTENCIA DEFINITIVA\nROL C-222-2025", page=2),
    ]
    for doc in docs:
        perfil.refinar(doc)
    grupos = agrupar(docs, perfil)
    assert len(grupos) == 2


def test_une_hojas_del_mismo_documento_y_rol():
    perfil = get_perfil("legal")
    docs = [
        _doc("SENTENCIA DEFINITIVA\nROL C-111-2025", page=1),
        _doc("SENTENCIA DEFINITIVA\n...continuacion de la sentencia...\nROL C-111-2025", page=2),
    ]
    for doc in docs:
        perfil.refinar(doc)
    grupos = agrupar(docs, perfil)
    assert len(grupos) == 1
    assert grupos[0].categoria == catalogo.CAT_RESOLUCIONES


def test_filas_incluyen_rol_y_tribunal():
    perfil = get_perfil("legal")
    doc = _doc(TEXTO_JUDICIAL, familia="resolucion")
    perfil.refinar(doc)
    fila = filas(agrupar([doc], perfil))[0]
    assert fila["rol"] == "C-1234-2025"
    assert "JUZGADO" in fila["tribunal"].upper()
    assert fila["parte_demandante"] == "JUAN PEREZ SOTO"


# ---------------------------------------------------------------------------
# Regresion: el perfil salud conserva el comportamiento historico
# ---------------------------------------------------------------------------

def test_salud_conserva_tipo_canonico_historico():
    perfil = get_perfil("salud")
    doc = _doc("BONO DE ATENCION FONASA\nPrestacion: consulta\nCopago $ 5.000",
               familia="documento_clinico")
    assert perfil.tipo_canonico(doc) == categorias.tipo_canonico(doc)


def test_salud_conserva_identificadores():
    perfil = get_perfil("salud")
    doc = _doc("BONO DE ATENCION", familia="bono_fonasa")
    doc.folio.set("123", "alta")
    doc.titular_rut.set("12.345.678-5", "alta")
    ids = perfil.identificadores(doc)
    assert ids["folio"] == "123"
    assert ids["rut"] == "12345678"


# ---------------------------------------------------------------------------
# Linea de comandos
# ---------------------------------------------------------------------------

def test_cli_acepta_perfil_legal_y_por_defecto_salud():
    parser = build_parser()
    assert parser.parse_args(["expediente", "--perfil", "legal"]).perfil == "legal"
    assert parser.parse_args(["expediente"]).perfil == "salud"
    assert parser.parse_args(["clasificar", "carpeta", "--perfil", "legal"]).perfil == "legal"


# ---------------------------------------------------------------------------
# Revisor HTML y round-trip de los campos del perfil
# ---------------------------------------------------------------------------

def test_revisor_muestra_y_exporta_campos_del_perfil(tmp_path):
    perfil = get_perfil("legal")
    doc = _doc(TEXTO_JUDICIAL, familia="resolucion")
    perfil.refinar(doc)
    expediente = Expediente(carpeta="caso", generado="2025-01-01", documentos=[doc])

    html = generar_revisor(expediente, tmp_path / "revision.html", perfil=perfil)
    texto = html.read_text(encoding="utf-8")
    assert "ROL / RIT" in texto
    assert "C-1234-2025" in texto
    assert '"rol"' in texto
    assert "tribunal" in texto


def test_from_dict_recupera_campos_planos_exportados_por_el_revisor():
    original = _doc(TEXTO_JUDICIAL, familia="resolucion")
    original.extra["rol"] = Field(value="C-1234-2025", confidence="alta")
    datos = original.to_dict()
    # El revisor exporta los campos del perfil planos (no dentro de "extra").
    datos["rol"] = {
        "value": "C-7777-2025",
        "confidence": "alta",
        "raw": "ROL C-7777-2025",
        "note": "",
        "edited": True,
    }

    recuperado = Document.from_dict(datos)
    assert recuperado.extra["rol"].value == "C-7777-2025"
    assert recuperado.extra["rol"].edited is True
