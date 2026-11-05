"""Pruebas de integracion del pipeline: modelo -> JSON -> revisor -> Word.

No ejecutan OCR (seria lento y no deterministico): construyen documentos con los
mismos objetos que produce el pipeline y verifican que todas las etapas
posteriores funcionan y que las rutas especiales (comprobante de tarjeta,
receta manuscrita, titular sin RUT) no rompen nada.
"""

import json

from docx import Document as DocxDocument

from documental.layout import build_lines, split_blocks
from documental.models import CONF_ALTA, CONF_FALTA, Document, Expediente, Field
from documental.ocr import Token
from documental.pipeline import (
    _attach_payment_voucher,
    _block_family,
    _is_noise,
    _propagar_folio,
)
from documental.revisor import cargar_expediente, generar_revisor
from documental.report_docx import generar_informe
from documental.titulares import TitularConfig, build_titulares, resolve_expediente


def block_from_text(text: str):
    tokens = []
    for row, line in enumerate(text.strip("\n").split("\n")):
        if not line.strip():
            continue
        top = 40 + row * 30
        tokens.append(
            Token(text=line.strip(), box=(60.0, float(top), 2420.0, top + 22.0), score=0.95)
        )
    return split_blocks(build_lines(tokens), page_height=3509)[0]


class TestClasificacionYRuido:
    def test_voucher_tarjeta_se_reconoce(self):
        bloque = block_from_text(
            "TRANSBANK\nVENTA EXENTA- COPIA CLIENTE\nTARJETA-DE DEBITO\nMONTO VENTA: $17.070"
        )
        familia, _, _ = _block_family(bloque)
        assert familia == "comprobante_pago"

    def test_receta_manuscrita_se_reconoce(self):
        bloque = block_from_text(
            "CENTRO OFTALMOLÓGICO VISION EN FAMILIA\nDr. Pablo Fuentes D.\n"
            "Oftalmólogo.\nRp. RUT: 11.111.111-1 ICM: 21.805-7\nT/Aont Nel Loneyal"
        )
        familia, _, _ = _block_family(bloque)
        assert familia == "receta_manuscrita"

    def test_encabezado_suelto_es_ruido(self):
        assert _is_noise(block_from_text("Fondo Nacional De Salud"))

    def test_documento_con_contenido_no_es_ruido(self):
        bloque = block_from_text("Fondo Nacional De Salud\nDATOS DE BENEFICIARIO(A)")
        assert not _is_noise(bloque)


class TestComprobanteDePago:
    def test_adjunta_medio_de_pago_y_monto(self):
        doc = Document(doc_id="a", source_file="f.pdf", page=1, index_in_page=1)
        voucher = block_from_text(
            "TRANSBANK\nTARJETA DE DEBITO\nMONTO VENTA: $17.070\nTOTAL: $17.070"
        )
        _attach_payment_voucher(voucher, [doc])
        assert doc.medio_pago.value == "Tarjeta de debito"
        assert doc.monto_total.value == 17070

    def test_sin_documentos_previos_no_falla(self):
        _attach_payment_voucher(block_from_text("TRANSBANK\nTARJETA DE DEBITO"), [])


class TestExpedienteCompleto:
    """Recorre JSON -> revisor -> Word con dos titulares."""

    def _expediente(self) -> Expediente:
        docs = []
        for index, (rut, nombre, monto) in enumerate(
            [
                ("12.345.678-5", "GLORIA ESTER SOTO PEREZ", 17070),
                ("20.217.034-4", "LUIS ANDRES SOTO PEREZ", 20000),
            ],
            start=1,
        ):
            doc = Document(
                doc_id=f"doc{index}", source_file="escaneo.pdf", page=index, index_in_page=1
            )
            doc.familia = "bono_fonasa"
            doc.tipo_documento = Field("Bono de atencion FONASA", CONF_ALTA, "BONO")
            doc.folio = Field(f"100{index}", CONF_ALTA, f"100{index}")
            doc.titular_nombre = Field(nombre, CONF_ALTA, nombre)
            doc.titular_rut = Field(rut, CONF_ALTA, rut)
            doc.fecha_emision = Field("2026-09-25", CONF_ALTA, "2026-09-25")
            doc.monto_total = Field(monto, CONF_ALTA, str(monto))
            docs.append(doc)
        config = [
            TitularConfig(rut="12.345.678-5", nombre="GLORIA ESTER SOTO PEREZ", relacion="madre"),
            TitularConfig(rut="", nombre="LUIS ANDRES SOTO PEREZ", relacion="hijo"),
        ]
        return resolve_expediente(
            docs, carpeta="/tmp/escaneos", generado="2026-10-26 12:00", config=config
        )

    def test_json_ida_y_vuelta(self, tmp_path):
        expediente = self._expediente()
        destino = tmp_path / "exp.json"
        destino.write_text(
            json.dumps(expediente.to_dict(), ensure_ascii=False), encoding="utf-8"
        )
        recargado = cargar_expediente(destino)
        assert len(recargado.documentos) == 2
        assert recargado.documentos[0].titular_rut.value == "12.345.678-5"

    def test_revisor_html_se_genera(self, tmp_path):
        expediente = self._expediente()
        html = generar_revisor(expediente, tmp_path / "rev.html")
        contenido = html.read_text(encoding="utf-8")
        assert "__DATOS__" not in contenido
        assert "GLORIA ESTER SOTO PEREZ" in contenido
        assert "btn-exportar" in contenido

    def test_informe_word_se_genera(self, tmp_path):
        expediente = self._expediente()
        destino = generar_informe(expediente, tmp_path / "informe.docx")
        assert destino.exists() and destino.stat().st_size > 5000
        word = DocxDocument(str(destino))
        texto = "\n".join(p.text for p in word.paragraphs)
        tablas = "\n".join(c.text for t in word.tables for r in t.rows for c in r.cells)
        assert "INFORME DE DOCUMENTACION MEDICA" in texto
        assert "GLORIA ESTER SOTO PEREZ" in tablas
        assert "Total general documentado" in texto

    def test_titular_sin_rut_se_marca_por_confirmar(self, tmp_path):
        expediente = self._expediente()
        # Escenario real: Carlos aparece en un documento sin RUT legible.
        expediente.documentos[1].titular_rut = Field(None, CONF_FALTA)
        expediente.titulares = build_titulares(
            expediente.documentos,
            [
                TitularConfig(rut="12.345.678-5", nombre="GLORIA ESTER SOTO PEREZ"),
                TitularConfig(rut="", nombre="LUIS ANDRES SOTO PEREZ"),
            ],
        )
        destino = generar_informe(expediente, tmp_path / "informe2.docx")
        tablas = "\n".join(
            c.text for t in DocxDocument(str(destino)).tables for r in t.rows for c in r.cells
        )
        assert "POR CONFIRMAR" in tablas

    def test_reporte_de_campos_por_verificar(self):
        doc = Document(doc_id="x", source_file="f.pdf", page=1, index_in_page=1)
        doc.familia = "bono_fonasa"
        doc.tipo_documento = Field("Bono FONASA", CONF_ALTA)
        doc.folio = Field(None, CONF_FALTA)
        doc.titular_nombre = Field("X", CONF_ALTA)
        doc.titular_rut = Field("12.345.678-5", CONF_ALTA)
        doc.fecha_emision = Field("2026-09-25", CONF_ALTA)
        doc.monto_total = Field(1000, CONF_ALTA)
        assert doc.campos_a_revisar() == ["folio"]
        assert doc.confianza_global() == CONF_FALTA


def _doc_simple(index: int, nombre: str | None, rut: str | None) -> Document:
    doc = Document(doc_id=f"d{index}", source_file="f.pdf", page=index, index_in_page=1)
    doc.familia = "bono_fonasa"
    doc.titular_nombre = Field(nombre, CONF_ALTA if nombre else CONF_FALTA, nombre)
    doc.titular_rut = Field(rut, CONF_ALTA if rut else CONF_FALTA, rut)
    return doc


class TestTitulares:
    """Regresiones detectadas al correr el pipeline sobre el expediente real."""

    def test_nombre_en_orden_distinto_no_duplica_titular(self):
        # FONASA imprime "APELLIDOS NOMBRES" y la boleta "NOMBRE APELLIDOS":
        # es la misma persona y no debe aparecer dos veces.
        docs = [
            _doc_simple(1, "SOTO PEREZ GLORIA ESTER", "12.345.678-5"),
            _doc_simple(2, "GLORIA ESTER SOTO PEREZ", None),
        ]
        titulares = build_titulares(docs, [])
        assert len(titulares) == 1
        assert titulares[0].rut == "12.345.678-5"

    def test_ficha_del_caso_fija_el_orden_del_nombre(self):
        # Cuando el caso declara el nombre, ese es el que se informa.
        docs = [
            _doc_simple(1, "SOTO PEREZ GLORIA ESTER", "12.345.678-5"),
            _doc_simple(2, "GLORIA ESTER SOTO PEREZ", None),
        ]
        config = [
            TitularConfig(
                rut="12.345.678-5",
                nombre="GLORIA ESTER SOTO PEREZ",
                relacion="titular principal",
            )
        ]
        titulares = build_titulares(docs, config)
        assert len(titulares) == 1
        assert titulares[0].nombre == "GLORIA ESTER SOTO PEREZ"
        assert titulares[0].relacion == "titular principal"

    def test_documento_sin_rut_se_une_aunque_llegue_primero(self):
        # El orden de los archivos escaneados no debe cambiar la agrupacion.
        docs = [
            _doc_simple(1, "GLORIA ESTER SOTO PEREZ", None),
            _doc_simple(2, "SOTO PEREZ GLORIA ESTER", "12.345.678-5"),
        ]
        assert len(build_titulares(docs, [])) == 1

    def test_rut_de_profesional_solo_no_crea_titular(self):
        # El RUT del doctor no identifica al paciente.
        doc = _doc_simple(1, None, "11.111.111-1")
        doc.profesional_rut = Field("11.111.111-1", CONF_ALTA, "Dr. Pablo Fuentes")
        assert build_titulares([doc], []) == []

    def test_nombre_truncado_por_ocr_se_une_al_titular_con_rut(self):
        docs = [
            _doc_simple(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5"),
            _doc_simple(2, "GLORIA ESTER SOT", None),
        ]
        titulares = build_titulares(docs, [])
        assert len(titulares) == 1
        assert titulares[0].rut == "12.345.678-5"

    def test_titular_declarado_sin_rut_queda_por_confirmar(self):
        docs = [_doc_simple(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5")]
        config = [
            TitularConfig(
                rut="12.345.678-5", nombre="GLORIA ESTER SOTO PEREZ", relacion="madre"
            ),
            TitularConfig(rut="", nombre="LUIS ANDRES SOTO PEREZ", relacion="hijo"),
        ]
        titulares = build_titulares(docs, config)
        assert len(titulares) == 2
        hijo = next(t for t in titulares if "LUIS" in t.nombre)
        assert hijo.rut == ""
        assert hijo.relacion == "hijo"


class TestEtiquetasDeFormulario:
    """Nombres de seccion de formulario no deben tomarse como nombre de persona."""

    def test_datos_persona_beneficiaria_no_es_nombre(self):
        from documental.normalizers import plausible_person_name

        assert not plausible_person_name("DATOS PERSONA BENEFICIARIA")
        assert not plausible_person_name("DATOS DEL PACIENTE")
        assert plausible_person_name("GLORIA ESTER SOTO PEREZ")




class TestFolioDeLaMismaHoja:
    """El numero de identificacion se hereda entre bloques de la misma hoja."""

    @staticmethod
    def _doc_hoja(index: int, page: int = 5) -> Document:
        return Document(
            doc_id=f"h{index}", source_file="f.pdf", page=page, index_in_page=index
        )

    def test_hereda_el_folio_de_otra_parte_de_la_hoja(self):
        con_folio = self._doc_hoja(1)
        con_folio.folio = Field("555000111", CONF_ALTA, "555000111")
        sin_folio = self._doc_hoja(2)
        _propagar_folio([con_folio, sin_folio])
        assert sin_folio.folio.value == "555000111"
        assert sin_folio.folio.confidence != CONF_ALTA  # queda para contrastar

    def test_no_hereda_si_la_hoja_tiene_dos_folios_distintos(self):
        # Dos bonos distintos en la misma hoja: cada uno con su numero.
        primero = self._doc_hoja(1)
        primero.folio = Field("111111111", CONF_ALTA, "111111111")
        segundo = self._doc_hoja(2)
        segundo.folio = Field("222222222", CONF_ALTA, "222222222")
        tercero = self._doc_hoja(3)
        _propagar_folio([primero, segundo, tercero])
        assert tercero.folio.is_empty

    def test_no_hereda_entre_hojas_distintas(self):
        uno = self._doc_hoja(1, page=5)
        uno.folio = Field("555000111", CONF_ALTA, "555000111")
        otro = self._doc_hoja(2, page=6)
        _propagar_folio([uno, otro])
        assert otro.folio.is_empty


class TestInformeWord:
    """El Word de trabajo no lleva imagenes: ya estan en el PDF del tribunal."""

    def _expediente(self, tmp_path):
        from PIL import Image

        render = tmp_path / "render"
        render.mkdir()
        Image.new("RGB", (400, 600), (245, 245, 245)).save(render / "recorte.png")
        doc = _doc_simple(1, "GLORIA ESTER SOTO PEREZ", "12.345.678-5")
        doc.imagen = "recorte.png"
        return resolve_expediente([doc], "carpeta", "2026-11-04"), render

    def test_por_defecto_no_inserta_imagenes(self, tmp_path):
        expediente, render = self._expediente(tmp_path)
        destino = generar_informe(expediente, tmp_path / "sin.docx", image_root=render)
        assert len(DocxDocument(str(destino)).inline_shapes) == 0

    def test_con_imagenes_las_inserta_y_pesa_mas(self, tmp_path):
        expediente, render = self._expediente(tmp_path)
        sin = generar_informe(expediente, tmp_path / "sin.docx", image_root=render)
        con = generar_informe(
            expediente,
            tmp_path / "con.docx",
            image_root=render,
            incluir_imagenes=True,
        )
        assert len(DocxDocument(str(con)).inline_shapes) == 1
        assert con.stat().st_size > sin.stat().st_size

