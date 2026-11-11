"""Catalogo del perfil legal: categorias, tipos canonicos y campos.

Los tipos canonicos son lo que el escrito cita ("Sentencia definitiva",
"Contrato de arriendo"). Reemplazan los encabezados sucios del OCR.
"""

from __future__ import annotations

import re
from datetime import date

from ...models import CONF_BAJA, CONF_MEDIA, Document, Field
from ...normalizers import fold, format_date_cl, parse_clp, parse_date
from ..base import CampoDef, Categoria
from .naturaleza import DOCTRINA, JURISPRUDENCIA, RESOLUCION

# ---------------------------------------------------------------------------
# Categorias (cada una es una carpeta de la salida ordenada)
# ---------------------------------------------------------------------------
CAT_ESCRITOS = "escritos"
CAT_RESOLUCIONES = "resoluciones"
CAT_NOTIFICACIONES = "notificaciones"
CAT_CONTRATOS = "contratos"
CAT_COMPROBANTES = "comprobantes"
CAT_PODERES = "poderes_certificados"
CAT_INFORMES = "informes"
CAT_JURISPRUDENCIA = "jurisprudencia"
CAT_RESOLUCIONES_ADMIN = "resoluciones_administrativas"
CAT_DOCTRINA = "doctrina"
CAT_OTROS = "otros"

CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(CAT_ESCRITOS, "Escritos", "01-expedientes/01-escritos"),
    Categoria(
        CAT_RESOLUCIONES,
        "Resoluciones judiciales",
        "01-expedientes/02-resoluciones-judiciales",
    ),
    Categoria(CAT_NOTIFICACIONES, "Notificaciones", "01-expedientes/03-notificaciones"),
    Categoria(CAT_INFORMES, "Informes y peritajes", "01-expedientes/04-informes-peritajes"),
    Categoria(CAT_JURISPRUDENCIA, "Jurisprudencia", "02-jurisprudencia"),
    Categoria(
        CAT_RESOLUCIONES_ADMIN,
        "Resoluciones administrativas",
        "03-resoluciones-administrativas",
    ),
    Categoria(CAT_DOCTRINA, "Doctrina", "04-doctrina"),
    Categoria(CAT_CONTRATOS, "Contratos", "05-documentos/01-contratos"),
    Categoria(CAT_COMPROBANTES, "Comprobantes de pago", "05-documentos/02-comprobantes"),
    Categoria(CAT_PODERES, "Poderes y certificados", "05-documentos/03-poderes-certificados"),
    Categoria(CAT_OTROS, "Otros documentos", "05-documentos/04-otros"),
)

# ---------------------------------------------------------------------------
# Tipos canonicos
# ---------------------------------------------------------------------------
T_DEMANDA = "Demanda"
T_CONTESTACION = "Contestacion de la demanda"
T_REPLICA = "Replica"
T_DUPLICA = "Duplica"
T_APELACION = "Recurso de apelacion"
T_CASACION = "Recurso de casacion"
T_REPOSICION = "Recurso de reposicion"
T_QUEJA = "Recurso de queja"
T_PRUEBA_ESCRITO = "Escrito de prueba"
T_ALEGATO = "Alegato"
T_DESISTIMIENTO = "Desistimiento o allanamiento"
T_ESCRITO = "Escrito"

T_SENTENCIA = "Sentencia definitiva"
T_AUTO = "Auto o sentencia interlocutoria"
T_AUTO_PRUEBA = "Auto de prueba"
T_PROVEIDO = "Proveido"
T_ACTA = "Acta de audiencia"
T_CERT_TRIBUNAL = "Certificado del tribunal"

T_CEDULA = "Cedula de notificacion"
T_NOTIF_ELECTRONICA = "Notificacion electronica"

T_CONTRATO_ARRENDAMIENTO = "Contrato de arriendo"
T_CONTRATO_TRABAJO = "Contrato de trabajo"
T_CONTRATO_COMPRAVENTA = "Contrato de compraventa"
T_CONTRATO_SERVICIOS = "Contrato de prestacion de servicios"
T_CONTRATO_MUTUO = "Contrato de mutuo"
T_CONTRATO = "Contrato"

T_BOLETA = "Boleta electronica"
T_FACTURA = "Factura electronica"
T_BOLETA_HONORARIOS = "Boleta de honorarios"
T_TRANSFERENCIA = "Comprobante de transferencia o deposito"
T_COMPROBANTE_PAGO = "Comprobante de pago"

T_PODER = "Poder notarial"
T_MANDATO = "Mandato judicial"
T_CERT_NACIMIENTO = "Certificado de nacimiento"
T_CERT_MATRIMONIO = "Certificado de matrimonio"
T_CERT_ANTECEDENTES = "Certificado de antecedentes"
T_CERT_VIGENCIA = "Certificado de vigencia o personeria"
T_CEDULA_IDENTIDAD = "Cedula de identidad o pasaporte"

T_INFORME_PERICIAL = "Informe pericial"
T_TASACION = "Tasacion"
T_INFORME_TECNICO = "Informe tecnico o social"

T_OFICIO = "Oficio"
T_CARTA = "Carta o correo"
T_ACTA_MEDIACION = "Acta de mediacion"
T_PAGARE = "Pagare"
T_CHEQUE = "Cheque"
T_SIN_CLASIFICAR = "Documento sin clasificar"

# Doctrina (v0.6)
T_DOCTRINA_LIBRO = "Libro"
T_DOCTRINA_CAPITULO = "Capitulo de libro"
T_DOCTRINA_ARTICULO = "Articulo de revista"
T_DOCTRINA_TESIS = "Tesis o memoria"
T_DOCTRINA_PUBLICACION = "Publicacion de doctrina"

# Jurisprudencia (v0.6)
T_JURISPRUDENCIA = "Sentencia (jurisprudencia)"
T_JURISPRUDENCIA_CS = "Sentencia de la Corte Suprema"
T_JURISPRUDENCIA_CA = "Sentencia de Corte de Apelaciones"
T_JURISPRUDENCIA_TC = "Sentencia del Tribunal Constitucional"

# Actos administrativos (v0.6)
T_RESOLUCION_ADMIN = "Resolucion administrativa"
T_DICTAMEN = "Dictamen"
T_SANCION = "Sancion administrativa"
T_SUMARIO = "Sumario administrativo"


# Penal (v0.3)
T_QUERELLA = "Querella"
T_DENUNCIA = "Denuncia"
T_FORMALIZACION = "Formalizacion de la investigacion"
T_ACUSACION = "Acusacion fiscal"
T_SOBRESEIMIENTO = "Sobreseimiento"
T_SENTENCIA_CONDENATORIA = "Sentencia condenatoria"
T_SENTENCIA_ABSOLUTORIA = "Sentencia absolutoria"
T_MEDIDA_CAUTELAR = "Medida cautelar"

# Familia (v0.3)
T_DIVORCIO = "Demanda de divorcio"
T_ALIMENTOS = "Demanda de alimentos"
T_CUIDADO_PERSONAL = "Demanda de cuidado personal"
T_RELACION_DIRECTA = "Demanda de relacion directa y regular"
T_MEDIDA_PROTECCION = "Medida de proteccion (VIF)"

TIPOS: dict[str, str] = {
    T_DEMANDA: CAT_ESCRITOS,
    T_CONTESTACION: CAT_ESCRITOS,
    T_REPLICA: CAT_ESCRITOS,
    T_DUPLICA: CAT_ESCRITOS,
    T_APELACION: CAT_ESCRITOS,
    T_CASACION: CAT_ESCRITOS,
    T_REPOSICION: CAT_ESCRITOS,
    T_QUEJA: CAT_ESCRITOS,
    T_PRUEBA_ESCRITO: CAT_ESCRITOS,
    T_ALEGATO: CAT_ESCRITOS,
    T_DESISTIMIENTO: CAT_ESCRITOS,
    T_ESCRITO: CAT_ESCRITOS,
    T_SENTENCIA: CAT_RESOLUCIONES,
    T_AUTO: CAT_RESOLUCIONES,
    T_AUTO_PRUEBA: CAT_RESOLUCIONES,
    T_PROVEIDO: CAT_RESOLUCIONES,
    T_ACTA: CAT_RESOLUCIONES,
    T_CERT_TRIBUNAL: CAT_RESOLUCIONES,
    T_CEDULA: CAT_NOTIFICACIONES,
    T_NOTIF_ELECTRONICA: CAT_NOTIFICACIONES,
    T_CONTRATO_ARRENDAMIENTO: CAT_CONTRATOS,
    T_CONTRATO_TRABAJO: CAT_CONTRATOS,
    T_CONTRATO_COMPRAVENTA: CAT_CONTRATOS,
    T_CONTRATO_SERVICIOS: CAT_CONTRATOS,
    T_CONTRATO_MUTUO: CAT_CONTRATOS,
    T_CONTRATO: CAT_CONTRATOS,
    T_BOLETA: CAT_COMPROBANTES,
    T_FACTURA: CAT_COMPROBANTES,
    T_BOLETA_HONORARIOS: CAT_COMPROBANTES,
    T_TRANSFERENCIA: CAT_COMPROBANTES,
    T_COMPROBANTE_PAGO: CAT_COMPROBANTES,
    T_PODER: CAT_PODERES,
    T_MANDATO: CAT_PODERES,
    T_CERT_NACIMIENTO: CAT_PODERES,
    T_CERT_MATRIMONIO: CAT_PODERES,
    T_CERT_ANTECEDENTES: CAT_PODERES,
    T_CERT_VIGENCIA: CAT_PODERES,
    T_CEDULA_IDENTIDAD: CAT_PODERES,
    T_INFORME_PERICIAL: CAT_INFORMES,
    T_TASACION: CAT_INFORMES,
    T_INFORME_TECNICO: CAT_INFORMES,
    T_OFICIO: CAT_OTROS,
    T_CARTA: CAT_OTROS,
    T_ACTA_MEDIACION: CAT_OTROS,
    T_PAGARE: CAT_OTROS,
    T_CHEQUE: CAT_OTROS,
    T_SIN_CLASIFICAR: CAT_OTROS,
    T_QUERELLA: CAT_ESCRITOS,
    T_DENUNCIA: CAT_ESCRITOS,
    T_ACUSACION: CAT_ESCRITOS,
    T_FORMALIZACION: CAT_RESOLUCIONES,
    T_SOBRESEIMIENTO: CAT_RESOLUCIONES,
    T_SENTENCIA_CONDENATORIA: CAT_RESOLUCIONES,
    T_SENTENCIA_ABSOLUTORIA: CAT_RESOLUCIONES,
    T_MEDIDA_CAUTELAR: CAT_RESOLUCIONES,
    T_DIVORCIO: CAT_ESCRITOS,
    T_ALIMENTOS: CAT_ESCRITOS,
    T_CUIDADO_PERSONAL: CAT_ESCRITOS,
    T_RELACION_DIRECTA: CAT_ESCRITOS,
    T_MEDIDA_PROTECCION: CAT_RESOLUCIONES,
    T_DOCTRINA_LIBRO: CAT_DOCTRINA,
    T_DOCTRINA_CAPITULO: CAT_DOCTRINA,
    T_DOCTRINA_ARTICULO: CAT_DOCTRINA,
    T_DOCTRINA_TESIS: CAT_DOCTRINA,
    T_DOCTRINA_PUBLICACION: CAT_DOCTRINA,
    T_JURISPRUDENCIA: CAT_JURISPRUDENCIA,
    T_JURISPRUDENCIA_CS: CAT_JURISPRUDENCIA,
    T_JURISPRUDENCIA_CA: CAT_JURISPRUDENCIA,
    T_JURISPRUDENCIA_TC: CAT_JURISPRUDENCIA,
    T_RESOLUCION_ADMIN: CAT_RESOLUCIONES_ADMIN,
    T_DICTAMEN: CAT_RESOLUCIONES_ADMIN,
    T_SANCION: CAT_RESOLUCIONES_ADMIN,
    T_SUMARIO: CAT_RESOLUCIONES_ADMIN,
}

CAMPOS: tuple[CampoDef, ...] = (
    CampoDef("rol", "ROL / RIT", True),
    CampoDef("tribunal", "Tribunal", True),
    CampoDef("caratula", "Caratula", True),
    CampoDef("parte_demandante", "Parte demandante"),
    CampoDef("parte_demandada", "Parte demandada"),
    CampoDef("tipo_parte", "Tipo de parte"),
    CampoDef("materia", "Materia"),
    CampoDef("cuaderno", "Cuaderno"),
    CampoDef("fojas", "Fojas"),
    CampoDef("etapa", "Etapa procesal"),
    CampoDef("abogado_patrocinante", "Abogado patrocinante"),
    CampoDef("abogado_apoderado", "Abogado apoderado"),
    CampoDef("notaria", "Notaria"),
    CampoDef("repertorio", "Repertorio"),
    CampoDef("fecha_notificacion", "Fecha de notificacion"),
    CampoDef("forma_notificacion", "Forma de notificacion"),
    CampoDef("monto_demanda", "Monto demandado"),
    CampoDef("monto_condena", "Monto de la condena"),
    CampoDef("moneda", "Moneda"),
    CampoDef("sociedad", "Sociedad"),
    CampoDef("giro", "Giro"),
)


def categoria_de_tipo(tipo: str) -> str:
    """Categoria (carpeta) a la que pertenece un tipo canonico."""
    return TIPOS.get(tipo, CAT_OTROS)


# Campos criticos segun la categoria del documento. Un contrato no tiene ROL y
# una notificacion no exige monto: el semaforo debe pedir solo lo que aplica.
CRITICOS_POR_CATEGORIA: dict[str, tuple[str, ...]] = {
    CAT_ESCRITOS: ("rol", "tribunal", "caratula"),
    CAT_RESOLUCIONES: ("rol", "tribunal", "fecha_emision"),
    CAT_NOTIFICACIONES: ("rol", "fecha_notificacion", "forma_notificacion"),
    CAT_CONTRATOS: ("fecha_emision",),
    CAT_COMPROBANTES: ("fecha_emision", "monto_total", "emisor_rut"),
    CAT_PODERES: ("fecha_emision", "notaria"),
    CAT_INFORMES: ("fecha_emision",),
    CAT_JURISPRUDENCIA: ("tribunal", "fecha_emision"),
    CAT_RESOLUCIONES_ADMIN: ("fecha_emision",),
    CAT_DOCTRINA: (),
    CAT_OTROS: ("fecha_emision",),
}


def criticos_para_tipo(tipo: str) -> tuple[str, ...]:
    """Campos criticos que exige un tipo canonico."""
    return CRITICOS_POR_CATEGORIA.get(categoria_de_tipo(tipo), CRITICOS_POR_CATEGORIA[CAT_OTROS])


# Certificado generico (los especificos se reconocen por su nombre).
T_CERTIFICADO = "Certificado"
TIPOS.setdefault(T_CERTIFICADO, CAT_PODERES)


def _texto(documento: Document) -> str:
    return fold(documento.texto_ocr or "")


def _cabecera(documento: Document, lineas: int = 3) -> str:
    """Primeras lineas con contenido: donde va el nombre del documento."""
    utiles = [linea.strip() for linea in (documento.texto_ocr or "").splitlines() if linea.strip()]
    return fold(" ".join(utiles[:lineas]))


def tipo_canonico(documento: Document) -> str:
    """Nombre canonico del instrumento, segun su texto y su familia."""
    texto = _texto(documento)
    cabecera = _cabecera(documento)
    familia = documento.familia
    naturaleza = getattr(documento, "naturaleza", "")

    # 0. Fuentes que no son piezas de un expediente.
    if naturaleza == DOCTRINA:
        if "tesis para optar" in texto or "memoria para optar" in texto:
            return T_DOCTRINA_TESIS
        if "capitulo" in cabecera or "capitulo de libro" in texto:
            return T_DOCTRINA_CAPITULO
        if "doi" in texto or "issn" in texto or "articulo" in cabecera:
            return T_DOCTRINA_ARTICULO
        if "isbn" in texto or "libro" in cabecera:
            return T_DOCTRINA_LIBRO
        return T_DOCTRINA_PUBLICACION
    if naturaleza == JURISPRUDENCIA:
        if "tribunal constitucional" in texto:
            return T_JURISPRUDENCIA_TC
        if "corte suprema" in texto:
            return T_JURISPRUDENCIA_CS
        if "corte de apelaciones" in texto:
            return T_JURISPRUDENCIA_CA
        return T_JURISPRUDENCIA
    if naturaleza == RESOLUCION:
        if "sumario" in texto:
            return T_SUMARIO
        if "dictamen" in texto or "contraloria" in texto:
            return T_DICTAMEN
        if "sancion" in texto or "multa" in texto:
            return T_SANCION
        return T_RESOLUCION_ADMIN

    # 1. Notificaciones (nombre propio en el encabezado).
    if "cedula de notificacion" in texto or "certifico que notifique" in texto:
        return T_CEDULA
    if "notificacion electronica" in texto:
        return T_NOTIF_ELECTRONICA

    # 1.5. Penal y familia (nombres propios; antes de las reglas genericas).
    if "querella" in cabecera:
        return T_QUERELLA
    if "denuncia" in cabecera:
        return T_DENUNCIA
    if "formalizacion de la investigacion" in texto:
        return T_FORMALIZACION
    if "acusacion fiscal" in texto or ("acusacion" in cabecera and "fiscal" in texto):
        return T_ACUSACION
    if "sobreseimiento" in texto:
        return T_SOBRESEIMIENTO
    if "sentencia condenatoria" in texto or ("condeno" in texto and "delito" in texto):
        return T_SENTENCIA_CONDENATORIA
    if "sentencia absolutoria" in texto or "absuelvo" in texto:
        return T_SENTENCIA_ABSOLUTORIA
    if "medida cautelar" in texto or "prision preventiva" in texto:
        return T_MEDIDA_CAUTELAR
    if "demanda de divorcio" in cabecera or "divorcio" in cabecera:
        return T_DIVORCIO
    if "demanda de alimentos" in cabecera or "pension de alimentos" in texto:
        return T_ALIMENTOS
    if "cuidado personal" in cabecera:
        return T_CUIDADO_PERSONAL
    if "relacion directa y regular" in texto or "regimen comunicacional" in texto:
        return T_RELACION_DIRECTA
    if "medida de proteccion" in texto or "violencia intrafamiliar" in texto:
        return T_MEDIDA_PROTECCION

    # 2. Resoluciones con nombre propio.
    if "sentencia definitiva" in texto:
        return T_SENTENCIA
    if (
        "auto de prueba" in texto
        or "recibese la causa a prueba" in texto
        or "recibase la causa a prueba" in texto
    ):
        return T_AUTO_PRUEBA
    if "acta de audiencia" in texto or "acta de la audiencia" in texto:
        return T_ACTA
    if "certifico" in cabecera and ("secretario" in texto or "tribunal" in texto):
        return T_CERT_TRIBUNAL

    # 3. Contratos con nombre propio (antes del contrato generico).
    if "contrato de arriendo" in cabecera or "contrato de arrendamiento" in cabecera:
        return T_CONTRATO_ARRENDAMIENTO
    if "contrato de trabajo" in cabecera:
        return T_CONTRATO_TRABAJO
    if "contrato de compraventa" in cabecera:
        return T_CONTRATO_COMPRAVENTA
    if "contrato de prestacion de servicios" in cabecera:
        return T_CONTRATO_SERVICIOS
    if "contrato de mutuo" in cabecera:
        return T_CONTRATO_MUTUO
    if "contrato" in cabecera:
        return T_CONTRATO

    # 4. Poderes y certificados.
    if "mandato judicial" in texto:
        return T_MANDATO
    if "poder notarial" in texto or "poder especial" in texto or "poder simple" in texto:
        return T_PODER
    if "certificado de nacimiento" in texto:
        return T_CERT_NACIMIENTO
    if "certificado de matrimonio" in texto:
        return T_CERT_MATRIMONIO
    if "certificado de antecedentes" in texto:
        return T_CERT_ANTECEDENTES
    if "certificado de vigencia" in texto or "personeria" in texto:
        return T_CERT_VIGENCIA
    if "cedula de identidad" in texto or "pasaporte" in texto:
        return T_CEDULA_IDENTIDAD
    if "certificado" in cabecera:
        return T_CERTIFICADO

    # 5. Informes y peritajes.
    if "informe pericial" in texto or "perito" in cabecera:
        return T_INFORME_PERICIAL
    if "tasacion" in texto or "avaluo" in texto or "valuacion" in texto:
        return T_TASACION
    if "informe tecnico" in texto or "informe social" in texto:
        return T_INFORME_TECNICO

    # 6. Recursos y escritos de parte.
    if "recurso de casacion" in texto or "casacion en la forma" in texto or "casacion en el fondo" in texto:
        return T_CASACION
    if "recurso de apelacion" in texto or "apelo" in texto:
        return T_APELACION
    if "recurso de reposicion" in texto or "reposicion" in cabecera:
        return T_REPOSICION
    if "recurso de queja" in texto:
        return T_QUEJA
    if "contestando la demanda" in texto or "contesto la demanda" in texto or "opongo excepciones" in texto:
        return T_CONTESTACION
    if "replica" in cabecera:
        return T_REPLICA
    if "duplica" in cabecera:
        return T_DUPLICA
    if "desisto" in texto or "me allano" in texto:
        return T_DESISTIMIENTO
    if "ofrezco prueba" in texto or "prueba documental" in texto:
        return T_PRUEBA_ESCRITO
    if "alegato" in texto:
        return T_ALEGATO
    if "demanda" in cabecera or ("en lo principal" in texto and "demanda" in texto):
        return T_DEMANDA

    # 7. Resoluciones genericas por estructura.
    if "vistos" in texto and ("considerando" in texto or "resuelvo" in texto):
        return T_AUTO
    if "por recibidos" in texto or "agreguese" in texto or "tengase presente" in texto or "proveyo" in texto:
        return T_PROVEIDO

    # 8. Escrito generico: "en lo principal", "solicito", "ruego".
    if "en lo principal" in texto or "solicito" in texto or "ruego" in texto:
        return T_ESCRITO

    # 9. Comprobantes de pago.
    if "boleta de honorarios" in texto:
        return T_BOLETA_HONORARIOS
    if "factura electronica" in texto or "factura" in cabecera:
        return T_FACTURA
    if "boleta electronica" in texto or "boleta exenta" in texto:
        return T_BOLETA
    if "comprobante de transferencia" in texto or "comprobante de deposito" in texto:
        return T_TRANSFERENCIA
    if "comprobante de pago" in texto:
        return T_COMPROBANTE_PAGO

    # 10. Otros documentos frecuentes en un expediente.
    if "acta de mediacion" in texto:
        return T_ACTA_MEDIACION
    if "pagare" in texto:
        return T_PAGARE
    if "cheque" in texto:
        return T_CHEQUE
    if "oficio" in cabecera:
        return T_OFICIO
    if "carta" in cabecera or "estimado" in texto or "correo electronico" in texto:
        return T_CARTA

    # 11. Ultimo recurso: familia detectada por el clasificador.
    return {
        "resolucion": T_AUTO,
        "escrito": T_ESCRITO,
        "contrato": T_CONTRATO,
        "comprobante": T_COMPROBANTE_PAGO,
        "notificacion": T_CEDULA,
        "poder_certificado": T_CERTIFICADO,
        "informe": T_INFORME_TECNICO,
    }.get(familia, T_SIN_CLASIFICAR)


# ---------------------------------------------------------------------------
# Extraccion de los datos propios del expediente judicial
# ---------------------------------------------------------------------------

_RE_ROL = re.compile(
    r"(?i)\b(?:rol|rit|rito)\s*(?:n[°º.]?\s*)?[:#]?\s*([A-Z]{0,4}[- ]?\d{1,6}[-/]\d{4})"
)
_RE_ROL_SUELTO = re.compile(r"\b([A-Z]{1,3}-\d{1,6}-\d{4})\b")
_RE_TRIBUNAL = re.compile(
    r"(?i)\b((?:\d{1,2}[°º]?\s*)?juzgado[^\n,.;]{0,60}"
    r"|corte de apelaciones de[^\n,.;]{0,50}"
    r"|tribunal[^\n,.;]{0,50})"
)
_RE_CARATULA = re.compile(r"(?i)car[aá]tula\s*[:.-]?\s*([^\n]{3,90})")
_RE_DEMANDANTE = re.compile(
    r"(?im)^\s*(?:parte\s+)?demandante\s*[:.-]\s*([^\n]{3,80})"
)
_RE_DEMANDADA = re.compile(
    r"(?im)^\s*(?:parte\s+)?demandad[oa]\s*[:.-]\s*([^\n]{3,80})"
)
_RE_FOJAS = re.compile(r"(?i)\b(?:fojas|fs\.?)\s*[:.-]?\s*(\d{1,4})\b")
_RE_PATROCINANTE = re.compile(
    r"(?i)(?:abogad[oa]\s+patrocinante|patrocinante|patrocina)\s*[:.-]?\s*([^\n]{3,80})"
)
_RE_NOTARIA = re.compile(r"(?i)notar[ií]a[^\n,.;]{0,60}")
_RE_REPERTORIO = re.compile(r"(?i)repertorio\s*(?:n[°º.]?\s*)?[:#]?\s*(\d{1,6})")
_RE_MONTO = re.compile(r"\$\s*([\d.]{4,})")

_MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}

_MATERIAS = (
    ("laboral", "Laboral"),
    ("juicio ejecutivo", "Ejecutivo"),
    ("cobranza", "Ejecutivo"),
    ("juicio ordinario", "Civil"),
    ("juicio sumario", "Civil"),
    ("violencia intrafamiliar", "Familia"),
    ("divorcio", "Familia"),
    ("pension de alimentos", "Familia"),
    ("cuidado personal", "Familia"),
    ("querella", "Penal"),
    ("formalizacion", "Penal"),
    ("sobreseimiento", "Penal"),
    ("delito", "Penal"),
    ("familia", "Familia"),
    ("penal", "Penal"),
)


def _valor_extra(documento: Document, nombre: str) -> str:
    campo = documento.extra.get(nombre)
    if campo is None or campo.value in (None, "", [], {}):
        return ""
    return str(campo.value).strip()


def _fijar(
    documento: Document,
    nombre: str,
    valor,
    confianza: str = CONF_MEDIA,
    raw: str = "",
    nota: str = "",
) -> None:
    """Guarda un campo extra sin sobrescribir un valor ya obtenido."""
    if valor in (None, "", [], {}):
        return
    campo = documento.extra.get(nombre)
    if campo is None:
        campo = Field()
        documento.extra[nombre] = campo
    campo.set(valor, confianza, raw, nota)


def _limpiar(valor: str | None, maximo: int = 90) -> str:
    return " ".join((valor or "").split()).strip(" ;:-")[:maximo]


def _fecha_de(texto: str) -> date | None:
    """Primera fecha legible del texto (dd-mm-aaaa o '12 de marzo de 2025')."""
    for encontrado in re.finditer(
        r"\b(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})\b", texto
    ):
        mes = _MESES.get(fold(encontrado.group(2)))
        if mes:
            try:
                return date(int(encontrado.group(3)), mes, int(encontrado.group(1)))
            except ValueError:
                continue
    for encontrado in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", texto):
        fecha = parse_date(encontrado.group(0))
        if fecha:
            return fecha if isinstance(fecha, date) else fecha.date()
    return None


def refinar(documento: Document, prestadores: tuple | None = None) -> None:
    """Completa ROL, tribunal, partes y demas datos leyendolos del texto OCR."""
    texto = documento.texto_ocr or ""
    if not texto.strip():
        return
    folded = fold(texto)

    if not _valor_extra(documento, "rol"):
        encontrado = _RE_ROL.search(texto) or _RE_ROL_SUELTO.search(texto)
        if encontrado:
            rol = _limpiar(encontrado.group(1).replace(" ", ""), 30).upper()
            _fijar(documento, "rol", rol, CONF_MEDIA, encontrado.group(0), "ROL leido del encabezado")

    if not _valor_extra(documento, "tribunal"):
        encontrado = _RE_TRIBUNAL.search(texto)
        if encontrado:
            _fijar(documento, "tribunal", _limpiar(encontrado.group(1)), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "caratula"):
        encontrado = _RE_CARATULA.search(texto)
        if encontrado:
            _fijar(documento, "caratula", _limpiar(encontrado.group(1)), CONF_MEDIA, encontrado.group(0))
        elif " con " in folded and ("demandante" in folded or "demandado" in folded):
            # "PEREZ CON BANCO X": la caratula suele ir en la primera linea.
            primera = _limpiar((texto.splitlines() or [""])[0])
            if " con " in fold(primera):
                _fijar(documento, "caratula", primera, CONF_BAJA, primera, "Caratula inferida")

    if not _valor_extra(documento, "parte_demandante"):
        encontrado = _RE_DEMANDANTE.search(texto)
        if encontrado:
            _fijar(documento, "parte_demandante", _limpiar(encontrado.group(1)), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "parte_demandada"):
        encontrado = _RE_DEMANDADA.search(texto)
        if encontrado:
            _fijar(documento, "parte_demandada", _limpiar(encontrado.group(1)), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "fojas"):
        encontrado = _RE_FOJAS.search(texto)
        if encontrado:
            _fijar(documento, "fojas", encontrado.group(1), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "abogado_patrocinante"):
        encontrado = _RE_PATROCINANTE.search(texto)
        if encontrado:
            _fijar(documento, "abogado_patrocinante", _limpiar(encontrado.group(1)), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "notaria"):
        encontrado = _RE_NOTARIA.search(texto)
        if encontrado:
            _fijar(documento, "notaria", _limpiar(encontrado.group(0)), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "repertorio"):
        encontrado = _RE_REPERTORIO.search(texto)
        if encontrado:
            _fijar(documento, "repertorio", encontrado.group(1), CONF_MEDIA, encontrado.group(0))

    if not _valor_extra(documento, "materia"):
        for clave, etiqueta in _MATERIAS:
            if clave in folded:
                _fijar(documento, "materia", etiqueta, CONF_BAJA, clave, "Materia inferida del texto")
                break

    if not _valor_extra(documento, "cuaderno"):
        if "cuaderno de ejecucion" in folded:
            _fijar(documento, "cuaderno", "Ejecucion", CONF_BAJA, "cuaderno de ejecucion")
        elif "cuaderno incidental" in folded:
            _fijar(documento, "cuaderno", "Incidental", CONF_BAJA, "cuaderno incidental")
        elif "cuaderno principal" in folded:
            _fijar(documento, "cuaderno", "Principal", CONF_BAJA, "cuaderno principal")

    if not _valor_extra(documento, "forma_notificacion"):
        if "notificacion personal" in folded or "notificado personalmente" in folded:
            _fijar(documento, "forma_notificacion", "Personal", CONF_MEDIA, "notificacion personal")
        elif "notificacion electronica" in folded:
            _fijar(documento, "forma_notificacion", "Electronica", CONF_MEDIA, "notificacion electronica")
        elif "por aviso" in folded:
            _fijar(documento, "forma_notificacion", "Por aviso", CONF_BAJA, "por aviso")

    if not documento.fecha_emision.value:
        fecha = _fecha_de(texto)
        if fecha:
            documento.fecha_emision.set(
                format_date_cl(fecha), CONF_MEDIA, "", "Fecha leida del documento"
            )

    if not _valor_extra(documento, "monto_demanda") and not _valor_extra(
        documento, "monto_condena"
    ):
        encontrado = _RE_MONTO.search(texto)
        if encontrado:
            monto = parse_clp(encontrado.group(1))
            if monto:
                nombre = "monto_condena" if "condeno" in folded else "monto_demanda"
                _fijar(documento, nombre, monto, CONF_MEDIA, encontrado.group(0))

    if not documento.emisor_nombre.value:
        emisor = _valor_extra(documento, "tribunal") or _valor_extra(documento, "notaria")
        if emisor:
            documento.emisor_nombre.set(emisor, CONF_MEDIA, "", "Tribunal o notaria que emite")

    if documento.naturaleza == JURISPRUDENCIA and not _valor_extra(documento, "tribunal"):
        for clave in ("corte suprema", "corte de apelaciones", "tribunal constitucional"):
            if clave in folded:
                _fijar(documento, "tribunal", clave.title(), CONF_MEDIA, clave,
                       "Tribunal inferido del encabezado")
                break


def detalle_de(documento: Document) -> str:
    """Frase corta y citable con los elementos que el escrito necesita."""
    partes: list[str] = []
    for nombre, etiqueta in (
        ("rol", "ROL"),
        ("tribunal", "tribunal"),
        ("caratula", "caratula"),
        ("parte_demandante", "demandante"),
        ("parte_demandada", "demandado"),
        ("fojas", "fojas"),
        ("notaria", "notaria"),
    ):
        valor = _valor_extra(documento, nombre)
        if valor:
            partes.append(f"{etiqueta}: {valor}")
    return "; ".join(partes[:5])





