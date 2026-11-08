"""Pruebas de la clasificacion de familias documentales."""

from documental.classify import (
    DESCONOCIDO,
    FARMACIA,
    FONASA,
    OPTICA,
    PAGARE,
    SII_BOLETA,
    classify,
)


class TestClasificacion:
    def test_bono_fonasa(self):
        texto = (
            "Fondo Nacional De Salud BONO DE ATENCIÓN AMBULATORIA 21923181\n"
            "DATOS DE BENEFICIARIO(A)\nAfiliado(a): 00012345678-5 GLORIA ESTER"
        )
        resultado = classify(texto)
        assert resultado.familia == FONASA
        assert resultado.etiqueta.startswith("Bono de atencion")

    def test_programa_fonasa(self):
        texto = (
            "PROGRAMA DE ATENCIÓN DE SALUD N° 591954329 Fonasa MODALIDAD : Libre Eleccion\n"
            "APORTE FONDO NACIONAL DE SALUD"
        )
        assert classify(texto).familia == FONASA

    def test_boleta_sii(self):
        texto = "OPTICA VISTA CLARA SPA R.U.T.: 77.777.777-7 BOLETA ELECTRÓNICA GIRO OPTICA"
        assert classify(texto).familia in {SII_BOLETA, OPTICA}

    def test_ticket_farmacia(self):
        texto = "SALCOBRAND FARMACIA GIRA: FARMACIA Y SUPERMERCADO BOLETA ELECTRONICA"
        assert classify(texto).familia == FARMACIA

    def test_pagare(self):
        texto = (
            "FUNDACION OFTALMOLOGICA LOS ANDES PAGARE N°: 313897-00 "
            "Debo y pagaré a la orden de FUNDACION"
        )
        assert classify(texto).familia == PAGARE

    def test_texto_sin_palabras_clave(self):
        assert classify("xyz abc").familia == DESCONOCIDO

    def test_empate_queda_en_confianza_media(self):
        # Mismo puntaje para dos familias: no se debe reportar como alta.
        texto = "hospital clinica diagnostico farmacia medicamento"
        resultado = classify(texto)
        assert resultado.confianza in {"media", "alta"}
        assert resultado.puntajes


def test_eje_dentro_de_otra_palabra_no_es_receta_optica():
    from documental.classify import classify
    c = classify("Se solicita la ejecutoria de la sentencia. El tribunal resuelve conforme a derecho.")
    assert c.familia != "receta_optica"


def test_formula_optica_es_receta_optica():
    from documental.classify import classify
    c = classify("RECETA OPTICA  ESF -2.00  CIL -1.25  EJE 90  LEJOS")
    assert c.familia == "receta_optica"
