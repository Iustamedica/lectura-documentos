"""Pruebas de los extractores usando textos OCR reales de este expediente.

Los textos estan copiados de la salida del OCR sobre los PDF originales, de modo
que las pruebas validan el comportamiento con el ruido real (no con texto ideal).
No requieren el motor OCR: se construyen tokens sinteticos con cajas simples.
"""

from documental.extractors import get_extractor
from documental.extractors.otros import extract_clinico
from documental.layout import build_lines, split_blocks
from documental.models import Document
from documental.ocr import Token


def block_from_text(text: str, *, width: int = 2480) -> object:
    """Construye un bloque de lineas a partir de texto plano (una linea por renglon)."""
    tokens = []
    for row, line in enumerate(text.strip("\n").split("\n")):
        if not line.strip():
            continue
        top = 40 + row * 30
        tokens.append(
            Token(text=line.strip(), box=(60.0, float(top), float(width - 60), top + 22.0), score=0.95)
        )
    lines = build_lines(tokens)
    return split_blocks(lines, page_height=3509)[0]


def make_doc(familia: str = "desconocido") -> Document:
    return Document(doc_id="test", source_file="test.pdf", page=1, index_in_page=1, familia=familia)


BONO_FONASA = """
Fondo Nacional De Salud BONO DE ATENCIÓN AMBULATORIA 21923181
Convenio: 15209 - Cen Oftal Centro Medico Ejemplo (LME)(Fact Aut Fecha Emisión: 2026-09-25 Hora: 13:57:22
DATOS DE BENEFICIARIO(A)
Afiliado(a): 00012345678-5 GLORIA ESTER SOTO PEREZ
Beneficiario(a): 00012345678-5 SOTO PEREZ GLORIA ESTER / Edad:71
Dirección: MAUCO ORIENTE 1833
Plan Grupo: B
0101204 1 CONSULTA MEDICA DE ESPECIALIDAD EN OFTALMOLOGIA $27.310 $10.240 $0 17370
Totales $27.310 $10.240 $2
A Pagar: S 17070
"""


class TestBonoFonasa:
    def test_extrae_identificacion(self):
        doc = get_extractor("bono_fonasa")(block_from_text(BONO_FONASA), make_doc())
        assert doc.folio.value == "21923181"
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.titular_nombre.value == "SOTO PEREZ GLORIA ESTER"
        assert doc.titular_edad.value == 71
        assert doc.titular_prevision.value == "FONASA tramo B"

    def test_extrae_fecha_y_monto(self):
        doc = get_extractor("bono_fonasa")(block_from_text(BONO_FONASA), make_doc())
        assert doc.fecha_emision.value == "2026-09-25"
        assert doc.fecha_atencion.value == "2026-09-25"
        assert doc.hora.value == "13:57:22"
        assert doc.monto_total.value == 17070

    def test_rut_ilegible_no_rompe(self):
        texto = BONO_FONASA.replace("00012345678-5 MARIA", "000780069Z-7 MARIA")
        doc = get_extractor("bono_fonasa")(block_from_text(texto), make_doc())
        # El segundo RUT (Beneficiario) sigue siendo valido y se usa.
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.titular_nombre.value == "SOTO PEREZ GLORIA ESTER"


BOLETA_SII = """
OPTI STORE SPA
ópticas R.U.T.: 78.445.210-7
SCHILLING BOLETA ELECTRÓNICA
GIRO OPTICA
VICYORIA 480 SANTIAGO CENTRO Casa Matriz 22 510 7203 N° 3605449
Señor (es): GLORIA ESTER SOTO PEREZ R.U.T.: 12.345.678-5
Fecha: 16/12/2025
ITEM DESCRIPCION CUOTAS CANTIDAD UNITARIO VALOR VALOR TOTAL
62 000 70000703 EXAMEN OPTOMETRICO 8.000 8.000
SUBTOTAL 8.000
TOTAL 3.900
"""


class TestFolioDelBonoRotado:
    """Bono escaneado girado: el folio va en el borde, sin su etiqueta al lado."""

    def test_folio_al_inicio_del_bloque_se_extrae(self):
        bloque = block_from_text(
            "860951008 VALIDO SOLO PARA ESTA FECHA DE EMISION\n"
            "Copago Otra Bonificacion* $2500 $2160 $10.330 A Pagar: $ 10330"
        )
        doc = make_doc()
        get_extractor("bono_fonasa")(bloque, doc)
        assert doc.folio.value == "860951008"

    def test_el_folio_no_se_confunde_con_el_monto(self):
        bloque = block_from_text(
            "860951008 VALIDO SOLO PARA ESTA FECHA DE EMISION\n"
            "Copago Otra Bonificacion* $2500 $2160 $10.330 A Pagar: $ 10330"
        )
        doc = make_doc()
        get_extractor("bono_fonasa")(bloque, doc)
        assert doc.monto_total.value == 10330

    def test_un_numero_corto_al_inicio_no_es_folio(self):
        bloque = block_from_text("12345 Copago $2500\nA Pagar: $ 2500")
        doc = make_doc()
        get_extractor("bono_fonasa")(bloque, doc)
        assert doc.folio.is_empty

    def test_un_rut_al_inicio_no_se_toma_como_folio(self):
        bloque = block_from_text("00012345678-5 GLORIA ESTER SOTO PEREZ\nA Pagar: $ 5000")
        doc = make_doc()
        get_extractor("bono_fonasa")(bloque, doc)
        assert doc.folio.is_empty


class TestBoletaSii:
    def test_extrae_titular_y_emisor(self):
        doc = get_extractor("boleta_sii")(block_from_text(BOLETA_SII), make_doc())
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.emisor_rut.value == "78.445.210-7"
        assert "OPTI STORE" in doc.emisor_nombre.value

    def test_extrae_fecha_folio_y_total(self):
        doc = get_extractor("boleta_sii")(block_from_text(BOLETA_SII), make_doc())
        assert doc.fecha_emision.value == "2025-12-16"
        # El OCR pega el folio al rotulo "BOLETA ELECTRONICA" ("N° 3605449").
        assert doc.folio.value is not None
        assert doc.folio.value.isdigit()
        assert doc.monto_total.value == 3900


PROGRAMA_FONASA = """
PROGRAMA DE ATENCIÓN DE SALUD N° 591954329
Fonasa MODALIDAD : Libre Eleccion TIPO PROGRAMA: Otro
DATOS PERSONA BENEFICIARIA RUT TITULAR RUT PACIENTE :12345678-5 DIRECCION : AV. EJEMPLO 1234 :12345678-5 NOMBRE REGISTRAL:GLORIA ESTER SOTO PEREZ
DIAGNOSTICO : LENTES OPTICOS LEJOS Y CERCA
COSTO TOTAL $ 48.520 A PAGAR PERSONA BENEFICIARIA $ 24.260
FECHA EMISIÓN : 08/07/2025
"""


class TestProgramaFonasa:
    def test_extrae_datos_programa(self):
        doc = get_extractor("bono_fonasa")(block_from_text(PROGRAMA_FONASA), make_doc())
        assert doc.folio.value == "591954329"
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"
        assert doc.fecha_emision.value == "2025-07-08"
        assert doc.monto_bruto.value == 48520
        assert doc.monto_copago.value == 24260
        assert "LENTES" in doc.diagnostico.value


PAGARE = """
FUNDACION OFTALMOLOGICA LOS ANDES PAGARE N°: 313897-00
Capital Total Adeudado : $ 214.619.-
Debo y pagaré a la orden de FUNDACION OFTALMOLOGICA LOS ANDES, RUT N° 71.457.900-2
"""


SOLICITUD_EXAMENES = """
CENTRO OFTALMOLÓGICO
FUENTES
VISIÓNEN FAMILIA
Solicitud de Exámenes
Nombre: 1on lidly CoevogeD Mego R.U.T.: 33.333.333-3
Diagnóstico:
Curva de Tensión Aplanática x 1 día 12-01-004 x2
Fecha: 25-9. L016 Médico: Firma: Dr. Pablo Fuentes Rut: 11.111.111-1 D.
"""

# Texto OCR de una receta oftalmologica de ejemplo (anonimizado). El RUT
# del oftalmologo aparece suelto tras "Rp." y su nombre en el renglon siguiente.
RECETA_RP = """
FUENTES CENTRO OFTALMOLÓGICO VISION ENFAMILIA
Rp. RUT: 11.111.111-1 ICM: 21.805-7 Dr. Pablo Fuentes D. Oftalmólogo.
oriz Holl
LOUTEN LATOF T A. Codina Imp, Lida, - Sontiago 1032 - F.: 225545369 - R.U.T.: 22.222.222-2
Axdo (tale 6 GAAP 2-1-2 Rut: 11.111.111-1 . PabbloFuentes D.
Cerro Colorado 5030 Of. 104Las Condes Santiago de Chile
Fono: (56) 2 2420 0100 clinica@ejemplo.cl
"""




class TestDocumentoClinico:
    def test_no_usa_el_rut_del_centro_medico(self):
        doc = get_extractor("documento_clinico")(block_from_text(SOLICITUD_EXAMENES), make_doc())
        # 33.333.333-3 es el RUT del centro oftalmologico y 11.111.111-1 el del
        # medico: ninguno puede quedar como RUT del paciente.
        assert doc.titular_rut.value is None
        assert doc.titular_rut.confidence == "baja"
        assert "no es legible" in doc.titular_rut.note

    def test_registra_al_medico_tratante(self):
        doc = get_extractor("documento_clinico")(block_from_text(SOLICITUD_EXAMENES), make_doc())
        assert doc.profesional_rut.value == "11.111.111-1"
        assert doc.titulo == "SOLICITUD DE EXÁMENES"

    def test_paciente_manuscrito_se_infiere_con_marcador(self):
        # Fragmento del OCR: el nombre manuscrito queda destruido, pero la
        # palabra "gloria" sobrevive pegada al ruido y permite reconocer al
        # titular (el OCR de manuscrito une palabras: "MAMAGLORIA").
        texto = SOLICITUD_EXAMENES.replace(
            "Nombre: 1on lidly CoevogeD Mego", "Nombre: MAMAGLORIA CAMWAM AOY"
        )
        doc = extract_clinico(
            block_from_text(texto), make_doc(), ["GLORIA ESTER SOTO PEREZ"]
        )
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"
        assert doc.titular_nombre.confidence == "baja"
        assert "confirmar" in doc.titular_nombre.note

    def test_manuscrito_irreconocible_no_se_asigna(self):
        # Si no queda ninguna palabra util, no se inventa un titular.
        doc = extract_clinico(
            block_from_text(SOLICITUD_EXAMENES), make_doc(), ["GLORIA ESTER SOTO PEREZ"]
        )
        assert doc.titular_nombre.value is None

    def test_sin_nombres_conocidos_no_inventa_paciente(self):
        doc = get_extractor("documento_clinico")(block_from_text(SOLICITUD_EXAMENES), make_doc())
        assert doc.titular_nombre.value is None

    def test_rut_suelto_del_medico_no_es_rut_del_paciente(self):
        # Bloque del pie del recibo (anonimizado): el RUT aparece junto a
        # "Rp." y el nombre del oftalmologo viene a continuacion. Sin paciente
        # identificado, ese RUT no puede crear un titular.
        doc = get_extractor("documento_clinico")(block_from_text(RECETA_RP), make_doc())
        assert doc.titular_rut.value is None
        assert doc.titular_rut.confidence == "baja"
        assert doc.profesional_rut.value == "11.111.111-1"

    def test_rut_en_el_pie_del_recibo_tampoco_es_del_paciente(self):
        # El mismo PDF se parte en dos bloques al detectar el OCR. El segundo
        # bloque solo trae el pie del recibo, donde el nombre del medico queda
        # a dos renglones del RUT ("Rut: 11.111.111-1 . PabbloFuentes D.").
        texto = """
LOUTEN LATOF T A. Codina Imp, Lida, - Sontiago 1032 - F.: 225545369 - R.U.T.: 22.222.222-2
Axdo (tale 6 GAAP 2-1-2 Rut: 11.111.111-1 . PabbloFuentes D.
Cerro Colorado 5030 Of. 104Las Condes Santiago de Chile
Fono: (56) 2 2420 0100 clinica@ejemplo.cl
"""
        doc = extract_clinico(block_from_text(texto), make_doc())
        assert doc.titular_rut.value is None
        assert doc.profesional_rut.value == "11.111.111-1"

    def test_rut_del_paciente_junto_a_una_direccion_se_conserva(self):
        # Una direccion tras el "Rut:" no debe confundirse con el medico: si el
        # formulario identifica al paciente, el RUT se conserva.
        texto = """
SOLICITUD DE EXAMENES
Nombre: GLORIA ESTER SOTO PEREZ
Rut: 12.345.678-5
Direccion: Cerro Colorado 5030 Of. 104
Fecha: 25-09-2026
"""
        doc = extract_clinico(block_from_text(texto), make_doc())
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"


class TestPagare:
    def test_extrae_emisor_y_monto(self):
        doc = get_extractor("pagare")(block_from_text(PAGARE), make_doc())
        assert doc.monto_total.value == 214619
        assert doc.folio.value == "313897"
        assert doc.emisor_rut.value == "71.457.900-2"
        assert "LOS ANDES" in doc.emisor_nombre.value

