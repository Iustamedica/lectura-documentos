"""Pruebas de los normalizadores chilenos (RUT, montos, fechas, texto)."""

from datetime import date

from documental.normalizers import (
    clean_name,
    find_all_ruts,
    fold,
    format_clp,
    format_rut,
    is_person_rut,
    looks_like_form_label,
    looks_like_person_name,
    names_overlap,
    parse_clp,
    parse_date,
    parse_rut,
    parse_time,
    plausible_person_name,
    roman_letters_to_digits,
    rut_dv,
    rut_is_prestador,
)


class TestRut:
    def test_digito_verificador_conocido(self):
        assert rut_dv(3456786) == "7"
        # El DV 1 corresponde al cuerpo 76093804 (76.093.804-1).
        assert rut_dv(76093804) == "1"

    def test_digito_verificador_k(self):
        assert rut_dv(12000008) == "K"

    def test_format_rut_con_miles(self):
        # Agrupa por miles con cuerpos de 7 y de 8 digitos.
        assert format_rut(3456785, "8") == "3.456.785-8"
        assert format_rut(12345678, "5") == "12.345.678-5"

    def test_parse_rut_formatos_varios(self):
        assert parse_rut("RUT: 12.345.678-5") == "12.345.678-5"
        assert parse_rut("12345678-5") == "12.345.678-5"
        assert parse_rut("00012345678-5") == "12.345.678-5"
        # Punto de miles mal puesto: 12.34567-5 -> cuerpo 1234567, DV 4.
        assert parse_rut("12.34567-4") == "1.234.567-4"

    def test_parse_rut_rechaza_dv_invalido(self):
        # El DV 8 no corresponde al cuerpo 12345678 (correcto es 5).
        assert parse_rut("12.345.678-8") is None
        assert parse_rut("12.345.678-8", validate=False) == "12.345.678-8"

    def test_parse_rut_con_ruido_ocr(self):
        assert parse_rut("O0011111111-1") == "11.111.111-1"

    def test_find_all_ruts_unicos(self):
        text = "Afiliado(a): 00012345678-5 y luego 12.345.678-5 y 11.111.111-1"
        assert find_all_ruts(text) == ["12.345.678-5", "11.111.111-1"]


class TestMontos:
    def test_parse_clp_formatos(self):
        assert parse_clp("$27.310") == 27310
        assert parse_clp("27.310") == 27310
        assert parse_clp("$ 16770") == 16770
        assert parse_clp("555.920") == 555920
        assert parse_clp("$0") == 0
        assert parse_clp("sin monto") is None
        assert parse_clp("") is None
        assert parse_clp(None) is None

    def test_parse_clp_ruido(self):
        assert parse_clp("$111.B60") == 111
        assert parse_clp("") is None
        assert parse_clp(None) is None

    def test_format_clp(self):
        assert format_clp(20000) == "$20.000"
        assert format_clp(555920) == "$555.920"
        assert format_clp(None) == ""


class TestFechas:
    def test_parse_date_numerica(self):
        assert parse_date("16/12/2025") == date(2025, 12, 16)
        assert parse_date("25-09-2026") == date(2026, 9, 25)
        assert parse_date("2026-09-25") == date(2026, 9, 25)
        assert parse_date("10.01.2024") == date(2024, 1, 10)

    def test_parse_date_texto(self):
        assert parse_date("24 de octubre de 2025") == date(2025, 10, 24)
        assert parse_date("25-mar-2024") == date(2024, 3, 25)

    def test_parse_date_invalida(self):
        assert parse_date("31/02/2025") is None
        assert parse_date("sin fecha") is None

    def test_parse_time(self):
        assert parse_time("Hora: 13:57:22") == "13:57:22"
        assert parse_time("a las 9:05") == "09:05"
        assert parse_time("sin hora") is None


class TestTexto:
    def test_fold_quita_tildes_y_minusculas(self):
        assert fold("BONO DE ATENCIÓN") == "bono de atencion"
        assert fold("  Prestación   Médica ") == "prestacion medica"

    def test_clean_name(self):
        assert clean_name("  GLORIA ESTER SOTO PEREZ  ") == "GLORIA ESTER SOTO PEREZ"
        assert clean_name("- NOMBRE: PEREZ") == "NOMBRE: PEREZ"

    def test_looks_like_person_name(self):
        assert looks_like_person_name("GLORIA ESTER SOTO PEREZ")
        assert looks_like_person_name("Luis Andres Soto Perez")
        assert not looks_like_person_name("TOTAL 20.000")
        assert not looks_like_person_name("BONO")
        assert not looks_like_person_name("Fecha Emision")


class TestRutPersonaVsEmpresa:
    """Protecciones para no asignar RUT de clinicas/emisores al paciente."""

    def test_rut_de_persona(self):
        assert is_person_rut("12.345.678-5")
        assert is_person_rut("11.111.111-1")
        assert is_person_rut("20.217.034-4")

    def test_rut_de_empresa_no_es_persona(self):
        assert not is_person_rut("33.333.333-3")  # Centro Oftalmologico
        assert not is_person_rut("77.777.777-7")  # Optica
        assert not is_person_rut("71.457.900-2")  # Fundacion
        assert not is_person_rut("76.305.804-2")  # Centro medico

    def test_rut_marcado_como_prestador(self):
        linea = "RUT PRESTADOR: 33.333.333-3"
        assert rut_is_prestador(linea, "33.333.333-3")

    def test_rut_de_paciente_no_es_prestador(self):
        linea = "Afiliado(a): 00012345678-5 GLORIA ESTER SOTO PEREZ"
        assert not rut_is_prestador(linea, "12.345.678-5")

    def test_etiquetas_de_formulario(self):
        assert looks_like_form_label("DATOS DE PRESTADOR")
        assert looks_like_form_label("COPIA CLIENTE")
        assert not looks_like_form_label("GLORIA ESTER SOTO PEREZ")


class TestFechasConRuidoOcr:
    def test_letras_romanas_en_dia_o_mes(self):
        # El OCR convierte "4-01-2026" en "4-0I-2026" y "2026" en "20026".
        assert parse_date(roman_letters_to_digits("4-0I-20026")) == date(2026, 1, 4)

    def test_numeral_romano_como_mes(self):
        assert parse_date(roman_letters_to_digits("25-XII-2025")) == date(2025, 12, 25)

    def test_no_altera_texto_que_no_es_fecha(self):
        original = "Dr. Pablo Fuentes Oftalmologo"
        assert roman_letters_to_digits(original) == original


class TestComparacionDeNombres:
    def test_nombres_truncados_por_ocr(self):
        assert names_overlap("GLORIA ESTER SOTO PEREZ", "GLORIA ESTER SOTO PEREZ")
        assert names_overlap("GLORIA ESTER SOTO PEREZ", "GLORIA ESTER SOT")
        assert not names_overlap("GLORIA ESTER SOTO PEREZ", "CENTRO OFTALMOLOGICO")


class TestNombrePlausible:
    """El OCR de letra manuscrita produce cadenas alfabeticas que no son nombres."""

    def test_nombres_reales_del_expediente(self):
        for nombre in (
            "GLORIA ESTER SOTO PEREZ",
            "SOTO PEREZ GLORIA ESTER",
            "LUIS ANDRES SOTO PEREZ",
            "Glorja Segura Perez",
            "Pablo Fuentes",
        ):
            assert plausible_person_name(nombre), nombre

    def test_ruido_de_letra_manuscrita(self):
        for ruido in (
            "MAMAGLORIA CAMWAM AOY",
            "T/Aont Nel Loneyal Anost",
            "1on lidly CoevogeD Mego",
            "MESENTA MAZEYN PiAE",
        ):
            assert not plausible_person_name(ruido), ruido

    def test_etiquetas_de_formulario_no_son_nombres(self):
        assert not plausible_person_name("DATOS DE PRESTADOR")

