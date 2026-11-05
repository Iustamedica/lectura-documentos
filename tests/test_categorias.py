"""Pruebas de las categorias documentales y del refinamiento del tipo.

Los textos de prueba reproducen el OCR real de los expedientes: mayusculas
sueltas, la "I" leida como "l", formulas opticas y formularios con la bajada
en medio de la hoja.
"""

from documental.categorias import (
    CAT_BOLETAS,
    CAT_BONOS,
    CAT_CERTIFICADOS,
    CAT_FICHAS,
    CAT_OTROS,
    CAT_RECETAS,
    Prestador,
    T_BONO_AMBULATORIO,
    T_BOLETA_FARMACIA,
    T_CERTIFICADO,
    T_EPICRISIS,
    T_EXAMEN_OPTICO,
    T_FICHA,
    T_RECETA,
    T_RECETA_LENTES,
    T_RECETA_MEDICAMENTOS,
    T_SOL_EXAMENES,
    T_SOL_INTERCONSULTA,
    T_SOL_PABELLON,
    T_SIN_CLASIFICAR,
    carpeta_de,
    categoria_de,
    limpiar_nombre,
    nombre_archivo,
    prestador_de,
    refinar,
    tipo_canonico,
    tipo_de_grupo,
)
from documental.models import Document


def _doc(texto: str, familia: str = "desconocido", **campos) -> Document:
    doc = Document(
        doc_id="x-1-1", source_file="a.pdf", page=1, index_in_page=1,
        familia=familia, texto_ocr=texto,
    )
    for nombre, valor in campos.items():
        getattr(doc, nombre).value = valor
    return doc


class TestTipoCanonico:
    def test_bono_ambulatorio_por_el_nombre_del_instrumento(self):
        doc = _doc("BONO DE ATENCION AMBULATORIA\nFOLIO 123\nRut Beneficiario")
        assert tipo_canonico(doc) == T_BONO_AMBULATORIO
        assert categoria_de(doc) == CAT_BONOS

    def test_programa_de_atencion_de_salud_es_un_bono(self):
        doc = _doc("PROGRAMA DE ATENCION DE SALUD N 591954329\nMODALIDAD Libre Eleccion")
        assert categoria_de(doc) == CAT_BONOS

    def test_boleta_de_farmacia(self):
        doc = _doc("FARMACIA CRUZ VERDE\nTICKET 001\nTOTAL $10.000")
        assert tipo_canonico(doc) == T_BOLETA_FARMACIA
        assert categoria_de(doc) == CAT_BOLETAS

    def test_epicrisis(self):
        doc = _doc("LOS ROBLES EPICRISIS 22/09/2023 16:17\nPaciente : X")
        assert tipo_canonico(doc) == T_EPICRISIS
        assert categoria_de(doc) == CAT_FICHAS

    def test_solicitud_de_pabellon(self):
        doc = _doc("SOLICITUD Y AUTORIZACION DE PABELLON\nNOMBRE PACIENTE")
        assert tipo_canonico(doc) == T_SOL_PABELLON

    def test_solicitud_de_examenes(self):
        doc = _doc("Solicitud de Examenes\nPACIENTE: X\nECG")
        assert tipo_canonico(doc) == T_SOL_EXAMENES

    def test_interconsulta_gana_sobre_la_palabra_receta(self):
        # El formulario pide "recetas y examenes": no es una receta.
        doc = _doc("SOLICITUD DE INTERCONSULTA O DERIVACION\nAdjuntar recetas y examenes")
        assert tipo_canonico(doc) == T_SOL_INTERCONSULTA
        assert categoria_de(doc) == CAT_FICHAS

    def test_certificado(self):
        doc = _doc("CERTIFICADO DE ATENCION PSICOLOGICA\nFecha 12-03-2026")
        assert tipo_canonico(doc) == T_CERTIFICADO
        assert categoria_de(doc) == CAT_CERTIFICADOS

    def test_receta_de_lentes(self):
        doc = _doc("RECETADE LENTES\nNOMBRE: X\nAMowt ESF OD: +2.75\nCYL OD: -1.50")
        assert tipo_canonico(doc) == T_RECETA_LENTES
        assert categoria_de(doc) == CAT_RECETAS

    def test_receta_de_medicamentos(self):
        doc = _doc("RECETA DE MEDICAMENTOS\nFOLIO: 538\nRP.\n1 GOTA EN OJO")
        assert tipo_canonico(doc) == T_RECETA_MEDICAMENTOS

    def test_receta_manuscrita(self):
        doc = _doc("RECETARIO\nNOMBRE: ...\nRP.\nTopteor", familia="receta_manuscrita")
        assert tipo_canonico(doc) == T_RECETA

    def test_biometria_no_es_receta_de_lentes(self):
        # La biometria trae "ESF/CIL/EJE" y el OCR lee la I como "l".
        doc = _doc(
            "Carl Zeiss lOLMaster Advanced Technology V. 7.3\n"
            "OD derecho K1: 43.72 D / 7.72 mm x 18\nAL: 22.68 mm",
            familia="receta_optica",
        )
        assert tipo_canonico(doc) == T_EXAMEN_OPTICO
        assert categoria_de(doc) == CAT_FICHAS

    def test_ficha_con_solo_paciente_y_prestador(self):
        doc = _doc("Centro de examenes\nPACIENTE: X\nControl", familia="documento_clinico")
        assert tipo_canonico(doc) == T_FICHA

    def test_texto_irrecuperable(self):
        doc = _doc("e pare Ven d ee enft hirmetopia")
        assert tipo_canonico(doc) == T_SIN_CLASIFICAR
        assert categoria_de(doc) == CAT_OTROS

    def test_un_tipo_corregido_a_mano_manda(self):
        doc = _doc("CERTIFICADO DE ATENCION", familia="documento_clinico")
        doc.tipo_documento.value = "Informe social"
        doc.tipo_documento.edited = True
        assert tipo_canonico(doc) == "Informe social"


class TestPrestador:
    SALUD = Prestador("Clinica Los Robles", (r"robles",))

    def test_usa_la_tabla_de_prestadores(self):
        doc = _doc("CLINICA LOS ROBLES SOLICITUD DE PABELLON")
        assert prestador_de(doc, (self.SALUD,)) == "Clinica Los Robles"

    def test_el_encabezado_decide_entre_dos_prestadores(self):
        # El pie de pagina menciona otro centro: manda el encabezado.
        otro = Prestador("Optica Vista Clara", (r"vista[ ]*clara",))
        doc = _doc("CLINICA LOS ROBLES\nOftalmologia y Cirugia Ocular\nFirma Vista Clara")
        assert prestador_de(doc, (self.SALUD, otro)) == "Clinica Los Robles"

    def test_busca_en_todo_el_texto_si_el_encabezado_es_ilegible(self):
        # El OCR de estos escaneos destroza el encabezado ("IN.1", "mmo"): sin
        # este respaldo las fichas quedarian todas sin prestador.
        doc = _doc("IN.1\nLOS ROBLES Salud de Calidad a su Alcance")
        assert prestador_de(doc, (self.SALUD,)) == "Clinica Los Robles"

    def test_respeta_el_emisor_ya_extraido(self):
        doc = _doc("cualquier texto", emisor_nombre="Optica El Mirador")
        assert prestador_de(doc, (self.SALUD,)) == "Optica El Mirador"

    def test_sin_senales_devuelve_vacio(self):
        assert prestador_de(_doc("Od Valores de longitud de eje"), ()) == ""


class TestRefinar:
    def test_normaliza_el_tipo_sucio_y_deja_el_original_anotado(self):
        doc = _doc(
            "LOS ROBLES EPICRISIS 22/09/2023 16:17\n"
            "Paciente : GLORIA ESTER SOTO PEREZ\n"
            "Identificacion: 12.345.678-5",
            familia="documento_clinico",
            tipo_documento="LOS ROBLES EPICRISIS 22/09/2023 16:17 IMPRESO POR",
        )
        refinar(doc)
        assert doc.tipo_documento.value == T_EPICRISIS
        assert "EPICRISIS 22/09/2023" in doc.tipo_documento.note

    def test_completa_paciente_rut_y_fecha_vacios(self):
        doc = _doc(
            "OPTICA VISTA CLARA\n"
            "Apellido: SOTO PEREZ, GLORIA ESTER\n"
            "Fecha nacim.: 02-02-1950 No. ident.: 12345678-5\n"
            "Fecha medicion: 18-07-2023",
            familia="documento_clinico",
        )
        refinar(doc)
        assert doc.titular_nombre.value == "SOTO PEREZ GLORIA ESTER"
        assert doc.titular_rut.value == "12.345.678-5"
        assert doc.fecha_atencion.value == "2023-07-18"

    def test_no_sobrescribe_un_dato_ya_leido(self):
        doc = _doc("Paciente: OTRA PERSONA\nNo. ident.: 11111111-1", familia="documento_clinico")
        doc.titular_nombre.value = "GLORIA ESTER SOTO PEREZ"
        refinar(doc)
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"

    def test_la_receta_deja_dicho_que_no_transcribe_el_medicamento(self):
        doc = _doc("RECETARIO\nRP.\n1 GOTA", familia="receta_manuscrita")
        refinar(doc)
        assert "manuscrit" in doc.observaciones.value

    def test_es_idempotente(self):
        doc = _doc("BONO DE ATENCION AMBULATORIA\nFOLIO 1")
        refinar(doc)
        primero = (doc.tipo_documento.value, doc.tipo_documento.note)
        refinar(doc)
        assert (doc.tipo_documento.value, doc.tipo_documento.note) == primero

    def test_descarta_el_rut_del_medico_como_rut_del_paciente(self):
        # El pie de pagina acredita la firma con el RUT del profesional. Si ese
        # bloque se une al del nombre del paciente, queda un par nombre/RUT que
        # no corresponde a ninguna persona.
        doc = _doc(
            "Solicitud de Examenes\nNombre: GLORIA ESTER SOTO PEREZ\n"
            "Medico: Firma: Dr. Luis Andres Rojas Rut:11.111.111-1",
            familia="documento_clinico",
        )
        doc.titular_rut.value = "11.111.111-1"
        doc.titular_rut.confidence = "media"
        doc.profesional_rut.value = "11.111.111-1"
        refinar(doc)
        assert doc.titular_rut.value is None
        assert doc.titular_rut.confidence == "baja"
        assert "profesional" in doc.titular_rut.note
        # El nombre del paciente se conserva: solo se descarta el RUT ajeno.
        assert doc.titular_nombre.value == "GLORIA ESTER SOTO PEREZ"

    def test_conserva_el_rut_cuando_es_distinto_al_del_profesional(self):
        doc = _doc("Paciente: GLORIA ESTER SOTO PEREZ", familia="documento_clinico")
        doc.titular_rut.value = "12.345.678-5"
        doc.profesional_rut.value = "11.111.111-1"
        refinar(doc)
        assert doc.titular_rut.value == "12.345.678-5"


class TestTipoDeGrupo:
    def test_ignora_el_fragmento_sin_clasificar(self):
        docs = [
            _doc("e pare Ven d ee", familia="desconocido"),
            _doc("RECETADE LENTES\nESF OD: +2.75\nCYL OD: -1.50", familia="receta_optica"),
        ]
        assert tipo_de_grupo(docs) == T_RECETA_LENTES

    def test_prefiere_el_tipo_concreto_sobre_la_ficha_generica(self):
        docs = [
            _doc("Control", familia="documento_clinico"),
            _doc("LOS ROBLES EPICRISIS 22/09/2023", familia="documento_clinico"),
        ]
        assert tipo_de_grupo(docs) == T_EPICRISIS

    def test_todo_ilegible(self):
        assert tipo_de_grupo([_doc("xxx")]) == T_SIN_CLASIFICAR


class TestNombres:
    def test_quita_lo_que_no_es_apto_para_un_archivo(self):
        assert limpiar_nombre('Bono: 12/03 "x"') == "Bono 12 03 x"

    def test_nombre_de_archivo_lleva_numero_fecha_tipo_y_folio(self):
        nombre = nombre_archivo(7, "Bono de atencion ambulatoria", "17-07-2023", "GLORIA", "555000111")
        assert nombre == "007 17-07-2023 Bono de atencion ambulatoria GLORIA folio 555000111.pdf"

    def test_carpeta_de_prestador(self):
        assert carpeta_de("Clinica Los Robles") == "CLINICA LOS ROBLES"
        assert carpeta_de("") == "SIN PRESTADOR IDENTIFICADO"


class TestPatrones:
    """Guardan contra un error que ya ocurrio dos veces en este proyecto.

    Si un patron queda escrito con la barra duplicada (``\\\\s``), en un raw
    string exige una barra invertida literal en el texto y el patron deja de
    calzar en silencio: el codigo corre, los tests de integracion pasan y el
    campo simplemente queda vacio.
    """

    def test_ningun_patron_queda_con_barra_duplicada(self):
        import documental.categorias as modulo

        doble = chr(92) * 2
        patrones = [
            (nombre, getattr(valor, "pattern", valor))
            for nombre, valor in vars(modulo).items()
            if nombre.startswith("_RE_")
        ]
        patrones += [
            (f"prestador {prestador.nombre}", patron)
            for prestador in modulo.PRESTADORES_DEFECTO
            for patron in prestador.patrones
        ]
        assert patrones, "no se encontraron patrones que revisar"
        for nombre, patron in patrones:
            assert doble not in patron, f"{nombre} tiene la barra duplicada"
