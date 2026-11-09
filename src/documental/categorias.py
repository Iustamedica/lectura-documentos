"""Categoria documental y nombre canonico de cada instrumento.

Un expediente mezcla generos que se individualizan de forma distinta y que, por
lo mismo, no se pueden listar con las mismas columnas:

    bonos          instrumento + emisor + folio + paciente + receptor
    boletas        boleta/factura electronica + sociedad y RUT + descripcion + valor
    fichas         nombre del documento + prestador + fecha de atencion
    recetas        paciente + fecha + prestador que firma (no el medicamento)
    certificados   emisor + fecha

Este modulo traduce el texto crudo del OCR a un **nombre canonico** del
instrumento (``tipo_canonico``) y a la **categoria** que agrupa el documento
(``categoria_de``). El nombre canonico reemplaza a los encabezados que el OCR
entrega sucios (``"CLINLCA LOS ROBLES SOLICITUD DE PABELLON"``, con el nombre del
centro mal leido), porque el escrito no puede citar un tipo de documento con
errores de lectura.

``refinar`` completa, ademas, los datos que faltan (paciente, RUT, fecha,
prestador) leyendolos otra vez del texto OCR ya guardado. Nunca sobrescribe un
dato existente: solo rellena vacios, y cada valor queda con su texto de origen y
una nota para el revisor.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .models import CONF_BAJA, CONF_MEDIA, Document
from .normalizers import (
    clean_name,
    fold,
    format_clp,
    format_date_cl,
    looks_like_form_label,
    parse_date,
    parse_rut,
    plausible_person_name,
)

# ---------------------------------------------------------------------------
# Categorias: cada una es una carpeta en la salida ordenada.
# ---------------------------------------------------------------------------

CAT_BONOS = "bonos"
CAT_BOLETAS = "boletas"
CAT_FICHAS = "fichas"
CAT_RECETAS = "recetas"
CAT_CERTIFICADOS = "certificados"
CAT_OTROS = "otros"

# (clave, etiqueta para el Word, nombre de carpeta). El orden es el del indice.
CATEGORIAS: tuple[tuple[str, str, str], ...] = (
    (CAT_BONOS, "Bonos de atencion", "01-bonos"),
    (CAT_BOLETAS, "Boletas y facturas", "02-boletas"),
    (CAT_FICHAS, "Fichas clinicas y examenes", "03-fichas"),
    (CAT_RECETAS, "Recetas", "04-recetas"),
    (CAT_CERTIFICADOS, "Certificados", "05-certificados"),
    (CAT_OTROS, "Otros documentos", "06-otros"),
)

CATEGORIA_ETIQUETA = {clave: etiqueta for clave, etiqueta, _ in CATEGORIAS}
CATEGORIA_CARPETA = {clave: carpeta for clave, _, carpeta in CATEGORIAS}
ORDEN_CATEGORIA = {clave: orden for orden, (clave, _, _) in enumerate(CATEGORIAS)}

# ---------------------------------------------------------------------------
# Nombres canonicos de los instrumentos (lo que cita el escrito).
# ---------------------------------------------------------------------------

T_BONO = "Bono de atencion FONASA"
T_BONO_AMBULATORIO = "Bono de atencion ambulatoria"
T_BONO_URGENCIA = "Bono de atencion de urgencia"
T_BONO_PROGRAMA = "Programa de atencion de salud FONASA"

T_BOLETA = "Boleta electronica"
T_BOLETA_EXENTA = "Boleta electronica exenta"
T_FACTURA = "Factura electronica"
T_BOLETA_FARMACIA = "Boleta de farmacia"

T_RECETA = "Receta medica"
T_RECETA_MEDICAMENTOS = "Receta de medicamentos"
T_RECETA_LENTES = "Receta de lentes"

T_CERTIFICADO = "Certificado"

T_EPICRISIS = "Epicrisis"
T_SOL_EXAMENES = "Solicitud de examenes"
T_SOL_PABELLON = "Solicitud de pabellon"
T_SOL_INTERCONSULTA = "Solicitud de interconsulta o derivacion"
T_DAU = "Dato de atencion de urgencia (DAU)"
T_INFORME_EXAMENES = "Informe de examenes"
T_EXAMEN_OPTICO = "Examen optico"
T_FICHA = "Ficha clinica"

T_PAGARE = "Pagare"
T_MANDATO = "Mandato"
T_PRESUPUESTO = "Presupuesto"
T_ACTA_MEDIACION = "Acta de mediacion"

# Tipos adicionales frecuentes en un expediente (Chile).
T_CERT_NACIMIENTO = "Certificado de nacimiento"
T_CERT_MATRIMONIO = "Certificado de matrimonio"
T_CERT_DEFUNCION = "Certificado de defuncion"
T_CERT_RESIDENCIA = "Certificado de residencia"
T_LICENCIA_MEDICA = "Licencia medica"
T_LIQUIDACION_SUELDO = "Liquidacion de sueldo"
T_CERT_COTIZACIONES = "Certificado de cotizaciones (AFP)"
T_COMPROBANTE_PAGO = "Comprobante de pago o transferencia"
T_CARTOLA = "Cartola o estado de cuenta"
T_CONTRATO = "Contrato"
T_PODER = "Poder"
T_ORDEN_ATENCION = "Orden de atencion"
T_CONSENTIMIENTO = "Consentimiento informado"

T_SIN_CLASIFICAR = "Documento sin clasificar"

# Nombre canonico -> categoria donde se archiva.
TIPO_CATEGORIA: dict[str, str] = {
    T_BONO: CAT_BONOS,
    T_BONO_AMBULATORIO: CAT_BONOS,
    T_BONO_URGENCIA: CAT_BONOS,
    T_BONO_PROGRAMA: CAT_BONOS,
    T_BOLETA: CAT_BOLETAS,
    T_BOLETA_EXENTA: CAT_BOLETAS,
    T_FACTURA: CAT_BOLETAS,
    T_BOLETA_FARMACIA: CAT_BOLETAS,
    T_RECETA: CAT_RECETAS,
    T_RECETA_MEDICAMENTOS: CAT_RECETAS,
    T_RECETA_LENTES: CAT_RECETAS,
    T_CERTIFICADO: CAT_CERTIFICADOS,
    T_EPICRISIS: CAT_FICHAS,
    T_SOL_EXAMENES: CAT_FICHAS,
    T_SOL_PABELLON: CAT_FICHAS,
    T_SOL_INTERCONSULTA: CAT_FICHAS,
    T_DAU: CAT_FICHAS,
    T_INFORME_EXAMENES: CAT_FICHAS,
    T_EXAMEN_OPTICO: CAT_FICHAS,
    T_FICHA: CAT_FICHAS,
    T_PRESUPUESTO: CAT_FICHAS,
    T_PAGARE: CAT_OTROS,
    T_MANDATO: CAT_OTROS,
    T_ACTA_MEDIACION: CAT_OTROS,
    T_CERT_NACIMIENTO: CAT_CERTIFICADOS,
    T_CERT_MATRIMONIO: CAT_CERTIFICADOS,
    T_CERT_DEFUNCION: CAT_CERTIFICADOS,
    T_CERT_RESIDENCIA: CAT_CERTIFICADOS,
    T_LICENCIA_MEDICA: CAT_CERTIFICADOS,
    T_LIQUIDACION_SUELDO: CAT_OTROS,
    T_CERT_COTIZACIONES: CAT_OTROS,
    T_COMPROBANTE_PAGO: CAT_OTROS,
    T_CARTOLA: CAT_OTROS,
    T_CONTRATO: CAT_OTROS,
    T_PODER: CAT_OTROS,
    T_ORDEN_ATENCION: CAT_FICHAS,
    T_CONSENTIMIENTO: CAT_FICHAS,
    T_SIN_CLASIFICAR: CAT_OTROS,
}

TIPOS_FICHA = frozenset(
    {
        T_EPICRISIS,
        T_SOL_EXAMENES,
        T_SOL_PABELLON,
        T_SOL_INTERCONSULTA,
        T_DAU,
        T_INFORME_EXAMENES,
        T_EXAMEN_OPTICO,
        T_FICHA,
    }
)

# ---------------------------------------------------------------------------
# Prestadores: el nombre canonico del centro que emite la ficha.
# ---------------------------------------------------------------------------

SIN_PRESTADOR = "Sin prestador identificado"


@dataclass(frozen=True)
class Prestador:
    """Nombre canonico de un prestador y los patrones que lo delatan en el OCR.

    Los patrones se comparan contra el texto plegado (minusculas sin tildes),
    por lo que deben escribirse ya plegados.
    """

    nombre: str
    patrones: tuple[str, ...]


# Prestadores de uso comun en Chile. Es solo un punto de partida: el caso puede
# reemplazar o ampliar la lista con un ``prestadores.json`` (ver
# ``cargar_prestadores``), que es lo recomendable para no fijar en el codigo
# nombres que pertenecen a un expediente concreto.
PRESTADORES_DEFECTO: tuple[Prestador, ...] = (
    Prestador("Cruz Verde", (r"cruz[ ]*verde",)),
    Prestador("Farmacias Ahumada", (r"farmacias?[ ]*ahumada", r"ahumada")),
    Prestador("Salcobrand", (r"salcobrand",)),
    Prestador("Farmacias Doctor Simi", (r"doctor[ ]*simi",)),
    Prestador("Laboratorio Clinico", (r"laboratorio[ ]*clinic",)),
    Prestador("Hospital del Salvador", (r"hospital[ ]*del[ ]*salvador",)),
)

# Marcas que identifican una razon social en un encabezado (heuristica generica
# cuando el prestador no esta en la tabla). No incluye palabras como
# "oftalmologia" o "salud", que aparecen en la bajada del documento y no son el
# nombre del emisor.
_MARCAS_ORGANIZACION = (
    "spa",
    "ltda",
    "limitada",
    "s.a.",
    "eirl",
    "clinica",
    "hospital",
    "centro medico",
    "centro de examenes",
    "laboratorio",
    "optica",
    "farmacia",
    "instituto",
    "fundacion",
    "isapre",
    "fonasa",
)


def cargar_prestadores(ruta: Path | None) -> tuple[Prestador, ...]:
    """Lee una tabla de prestadores desde JSON y la antepone a la de defecto.

    Formato del archivo::

        [{"nombre": "Clinica Los Robles", "patrones": ["robles"]},
         {"nombre": "Optica Vista Clara", "patrones": ["vista[ ]*clara"]}]

    Los patrones se pliegan igual que el texto del OCR, de modo que
    ``"Los Robles"`` escrito con o sin tilde calza igual.
    """
    if ruta is None:
        return PRESTADORES_DEFECTO
    ruta = Path(ruta)
    if not ruta.is_file():
        return PRESTADORES_DEFECTO
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    propios = [
        Prestador(str(item["nombre"]), tuple(fold(p) for p in item.get("patrones", [])))
        for item in datos
        if item.get("nombre") and item.get("patrones")
    ]
    return tuple(propios) + PRESTADORES_DEFECTO


# ---------------------------------------------------------------------------
# Lectura del texto del documento
# ---------------------------------------------------------------------------


def texto_de(documento: Document) -> str:
    """Texto del documento plegado: OCR + tipo + titulo, para buscar patrones."""
    partes = [
        str(documento.texto_ocr or ""),
        str(documento.tipo_documento.value or ""),
        str(documento.titulo or ""),
    ]
    return fold(" ".join(parte for parte in partes if parte))


def _lineas(documento: Document, maximo: int = 4) -> list[str]:
    """Primeras lineas con contenido del OCR (el encabezado del documento)."""
    lineas = [
        linea.strip()
        for linea in str(documento.texto_ocr or "").splitlines()
        if len(linea.strip()) >= 3
    ]
    return lineas[:maximo]


def _valor(documento: Document, campo: str):
    return documento.field(campo).value


def prestador_de(
    documento: Document,
    prestadores: tuple[Prestador, ...] | None = None,
) -> str:
    """Nombre canonico del prestador que emite la ficha (vacio si no se sabe).

    Se prueba primero el encabezado del documento (las dos primeras lineas) y
    solo despues el texto completo: en documentos con firma, el nombre de otro
    centro aparece al pie y no es el emisor.
    """
    propio = str(_valor(documento, "emisor_nombre") or "").strip()
    if propio:
        return propio

    tabla = prestadores if prestadores is not None else PRESTADORES_DEFECTO
    lineas = _lineas(documento, 2)
    for ambito in (fold(" ".join(lineas)), texto_de(documento)):
        if not ambito:
            continue
        for prestador in tabla:
            if any(re.search(patron, ambito) for patron in prestador.patrones):
                return prestador.nombre

    # Heuristica generica: razon social en el encabezado. Se toma la marca de
    # organizacion (clinica, hospital, laboratorio...) y hasta 3 palabras que la
    # siguen, para no devolver una linea entera ("2026 Historial ... Clinica
    # Alemana") como si fuera el nombre del prestador.
    for linea in _lineas(documento, 3):
        if looks_like_form_label(linea):
            continue
        palabras = linea.split()
        for i, palabra in enumerate(palabras):
            plegada = fold(palabra)
            if any(marca in plegada for marca in _MARCAS_ORGANIZACION):
                candidato = clean_name(" ".join(palabras[i:i + 4]))
                if 4 <= len(candidato) <= 60:
                    return candidato.upper()
    return ""


# ---------------------------------------------------------------------------
# Nombre canonico del instrumento
# ---------------------------------------------------------------------------

_RE_RECETA = re.compile(r"(?<![a-z])r[ ]*p(?![a-z])|receta")
_RE_LENTES = re.compile(r"(?<![a-z])(?:esf|cil|eje|add|dp)(?![a-z])")
# Marcas de una biometria ocular (IOLMaster y similares). El OCR lee la "I"
# inicial como "l", de ahi la clase [il].
_RE_BIOMETRIA = re.compile(
    r"[il]olmaster|(?<![a-z])k1(?![a-z])|(?<![a-z])k2(?![a-z])|longitud de eje|"
    r"refr[.]? aspirada|queratometr|biometr|camara anterior|(?<![a-z])snr(?![a-z])|"
    r"haigis|holladay|(?<![a-z])srk(?![a-z])|lenstec|zeiss"
)
_RE_IDENT = re.compile(r"no[.]?[ ]*ident|fecha[ ]+de[ ]+medi(?:ci[oó]n|cion)|fecha[ ]+medi(?:ci[oó]n|cion)")


def _parece_biometria(texto: str) -> bool:
    """True si el texto es una medicion ocular y no una receta de lentes.

    La formula de lentes y la biometria comparten siglas (ESF/CIL/EJE), por lo
    que hay que mirar las marcas propias del equipo antes de decidir.
    """
    if _RE_BIOMETRIA.search(texto):
        return True
    return bool(_RE_IDENT.search(texto) and "apellido" in texto)


def _es_formula_de_lentes(texto: str) -> bool:
    """True si el texto trae una formula optica completa (al menos dos siglas)."""
    return len(set(_RE_LENTES.findall(texto))) >= 2


def tipo_canonico(documento: Document) -> str:
    """Nombre canonico del instrumento, deducido del OCR y de la familia.

    El orden de las comprobaciones importa: un bono puede contener la palabra
    "certificado" y una biometria puede contener "ESF", por lo que los generos
    con senales mas fuertes se resuelven antes.
    """
    texto = texto_de(documento)
    familia = documento.familia

    # Un tipo corregido a mano en el revisor manda sobre cualquier deduccion.
    if documento.tipo_documento.edited and documento.tipo_documento.value:
        return str(documento.tipo_documento.value)

    # 1. Bonos FONASA: manda el nombre del propio instrumento.
    if (
        familia == "bono_fonasa"
        or "bono de atencion" in texto
        or "programa de atencion de salud" in texto
    ):
        if "ambulatoria" in texto:
            return T_BONO_AMBULATORIO
        if "urgencia" in texto:
            return T_BONO_URGENCIA
        if "programa de atencion de salud" in texto:
            return T_BONO_PROGRAMA
        return T_BONO

    # 2. Boletas y facturas electronicas.
    if "factura" in texto and "electronica" in texto:
        return T_FACTURA
    if "boleta electronica exenta" in texto or "boleta exenta" in texto:
        return T_BOLETA_EXENTA
    farmacia = familia == "ticket_farmacia" or (
        "farmacia" in texto
        and ("ticket" in texto or "boleta" in texto or "comprobante" in texto)
    )
    if farmacia:
        return T_BOLETA_FARMACIA
    if (
        "boleta electronica" in texto
        or "boleta de honorarios" in texto
        or familia == "boleta_sii"
    ):
        return T_BOLETA

    # 2.5. Certificados con tipo especifico (Registro Civil, salud, laboral).
    if "certificado de nacimiento" in texto:
        return T_CERT_NACIMIENTO
    if "certificado de matrimonio" in texto:
        return T_CERT_MATRIMONIO
    if "certificado de defuncion" in texto:
        return T_CERT_DEFUNCION
    if "certificado de residencia" in texto:
        return T_CERT_RESIDENCIA
    if "licencia medica" in texto:
        return T_LICENCIA_MEDICA

    # 3. Certificados. El documento se titula "certificado" en el encabezado;
    #    la palabra suelta en el cuerpo no basta (una epicrisis puede mencionar
    #    un certificado de defuncion).
    if "certificado" in fold(" ".join(_lineas(documento, 2))) or "certificado de atencion" in texto:
        return T_CERTIFICADO

    # 4. Recetas con nombre propio en el encabezado (senal fuerte). La biometria
    #    ocular usa "ESF/CIL/EJE" sin ser una receta, por eso se descarta antes
    #    de mirar la formula optica.
    biometria = _parece_biometria(texto)
    if not biometria and (
        "receta de lentes" in texto
        or "recetade lentes" in texto
        or (_RE_RECETA.search(texto) and _RE_LENTES.search(texto))
        or _es_formula_de_lentes(texto)
    ):
        return T_RECETA_LENTES
    if "receta de medicamentos" in texto:
        return T_RECETA_MEDICAMENTOS

    # 5. Fichas clinicas con nombre propio en la bajada. Van antes de la receta
    #    generica porque estos formularios mencionan "receta" en su texto
    #    (una solicitud de interconsulta pide "recetas y examenes") y no son
    #    recetas.
    if "epicrisis" in texto:
        return T_EPICRISIS
    if "pabellon" in texto and ("solicitud" in texto or "autorizacion" in texto):
        return T_SOL_PABELLON
    if "interconsulta" in texto or "derivacion" in texto:
        return T_SOL_INTERCONSULTA
    if "solicitud de examenes" in texto or "solicitud de examen" in texto:
        return T_SOL_EXAMENES
    if (
        "dato de atencion de urgencia" in texto
        or "d a u" in texto
        or "atencion de urgencia" in texto
    ):
        return T_DAU
    if biometria:
        return T_EXAMEN_OPTICO
    if "examenes realizados" in texto or "informe de examenes" in texto:
        return T_INFORME_EXAMENES
    if "presupuesto" in texto:
        return T_PRESUPUESTO

    # 6. Receta generica: "Rp." o la palabra "receta" sin mas senales.
    if _RE_RECETA.search(texto) or familia in {"receta_manuscrita", "receta_optica"}:
        return T_RECETA

    # 7. Documentos que no son de salud, con nombre propio en el encabezado.
    #    Van antes de la ficha generica porque un mandato esta impreso en el
    #    mismo formulario que una ficha y si no se nombra se pierde.
    if "acta de" in texto and ("audiencia" in texto or "mediacion" in texto):
        return T_ACTA_MEDIACION
    if "mandato" in texto:
        return T_MANDATO
    if familia == "pagare" or "pagare" in texto:
        return T_PAGARE

    # 7.5. Otros documentos clinicos con nombre propio en el encabezado.
    if "consentimiento informado" in texto:
        return T_CONSENTIMIENTO
    if "orden de atencion" in texto or "orden de prestacion" in texto:
        return T_ORDEN_ATENCION

    # 8. Ficha clinica generica (solo paciente y prestador en el encabezado).
    if familia in {"documento_clinico", "resultado_laboratorio"}:
        return T_FICHA

    # 9. Documentos NO clinicos frecuentes en un expediente (van a "otros").
    cabecera = fold(" ".join(_lineas(documento, 2)))
    if "contrato" in cabecera:
        return T_CONTRATO
    if "poder especial" in texto or "poder notarial" in texto or "poder simple" in texto:
        return T_PODER
    if "liquidacion de sueldo" in texto or "liquidacion de remuneracion" in texto:
        return T_LIQUIDACION_SUELDO
    if "certificado de cotizaciones" in texto or ("cotizaciones" in texto and "afp" in texto):
        return T_CERT_COTIZACIONES
    if "cartola" in texto or "estado de cuenta" in texto:
        return T_CARTOLA
    if (
        "comprobante de pago" in texto
        or "comprobante de transferencia" in texto
        or "transferencia bancaria" in texto
        or "comprobante de deposito" in texto
    ):
        return T_COMPROBANTE_PAGO
    return T_SIN_CLASIFICAR


def tipo_de_grupo(documentos: list[Document]) -> str:
    """Nombre canonico que representa a un documento de varias hojas.

    Se descarta lo que no aporta ("Documento sin clasificar") y se prefiere el
    tipo concreto sobre la ficha generica, para que el nombre del grupo no quede
    determinado por el orden en que el layout entrego los bloques.
    """
    tipos = [tipo_canonico(documento) for documento in documentos]
    utiles = [tipo for tipo in tipos if tipo != T_SIN_CLASIFICAR]
    if not utiles:
        return T_SIN_CLASIFICAR
    concretos = [tipo for tipo in utiles if tipo != T_FICHA]
    candidatos = concretos or utiles
    conteo: dict[str, int] = {}
    for tipo in candidatos:
        conteo[tipo] = conteo.get(tipo, 0) + 1
    # A igualdad de apariciones gana el primero: es el del encabezado.
    return max(conteo, key=lambda tipo: (conteo[tipo], -candidatos.index(tipo)))


def categoria_de(documento: Document) -> str:
    """Categoria (carpeta) a la que pertenece el documento."""
    return categoria_de_tipo(tipo_canonico(documento))


def categoria_de_tipo(tipo: str) -> str:
    """Categoria que corresponde a un nombre canonico de documento."""
    return TIPO_CATEGORIA.get(tipo, CAT_OTROS)


# ---------------------------------------------------------------------------
# Refinamiento: completar lo que el extractor no alcanzo a leer
# ---------------------------------------------------------------------------

_RE_NOMBRE = (
    r"(?i:apellido|apellidos|paciente|nombre(?:[ ]+completo)?s?)[ ]*:?[ ]*"
    r"([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ,.]{5,60})"
)
_RE_RUT = (
    r"(?:no[.]?[ ]*ident[.]?|identificaci[oó]n|rut(?:[ ]+(?:del[ ]+)?paciente)?)"
    r"[ ]*:?[ ]*([0-9.]{6,12}[ ]*-[ ]*[0-9Kk])"
)
_RE_FECHA = (
    r"(?:fecha[ ]+de[ ]+medici[oó]n|fecha[ ]+medici[oó]n|fecha[ ]+de[ ]+atenci[oó]n|"
    r"fecha[ ]+atencion|fecha[ ]+de[ ]+ingreso|fecha[ ]+ingreso|fecha)[ ]*:?[ ]*"
    r"([0-9]{1,2}[ ]*(?:[/.-]|de)[ ]*"
    r"(?:[0-9]{1,2}|[A-Za-zÁÉÍÓÚÑáéíóúñ]{3,10})[ ]*(?:[/.-]|de)[ ]*[0-9]{2,4})"
)


def _fijar_tipo(documento: Document, tipo: str) -> None:
    """Escribe el nombre canonico sin que ``Field.set`` lo rechace por confianza.

    ``Field.set`` solo reemplaza el valor cuando el nuevo es mejor, y el tipo que
    entrego el extractor puede estar marcado como confianza alta aunque el texto
    venga sucio ("CLINLCA LOS ROBLES SOLICITUD DE PABELLON"). El nombre canonico
    no es un dato leido sino una etiqueta controlada, por lo que se asigna
    directamente.
    """
    anterior = str(documento.tipo_documento.value or "").strip()
    documento.tipo_documento.value = tipo
    if documento.tipo_documento.confidence in (None, "", "faltante"):
        documento.tipo_documento.confidence = CONF_MEDIA
    if anterior and anterior.upper() != tipo.upper():
        documento.tipo_documento.note = f"Encabezado leido por el OCR: {anterior}"
    documento.tipo_documento.raw = documento.tipo_documento.raw or anterior


def _completar_desde_texto(
    documento: Document,
    tipo: str,
    prestadores: tuple[Prestador, ...] | None = None,
) -> None:
    """Rellena paciente, RUT, fecha y prestador que el extractor dejo vacios."""
    texto = str(documento.texto_ocr or "")
    if not texto:
        return

    if documento.titular_nombre.is_empty:
        encontrado = re.search(_RE_NOMBRE, texto)
        if encontrado:
            # "APELLIDOS, NOMBRES" se deja como "APELLIDOS NOMBRES": el titulado
            # de estos formularios usa la coma y el escrito no la necesita.
            candidato = " ".join(clean_name(encontrado.group(1)).replace(",", " ").split())
            # No basta con descartar etiquetas de formulario: "SANTIAGO" o
            # "PACIENTE FECHA SOLICITUD" pasan ese filtro y no son personas.
            if plausible_person_name(candidato):
                documento.titular_nombre.set(
                    candidato.upper(),
                    CONF_MEDIA,
                    encontrado.group(0),
                    "Nombre tomado del encabezado al ordenar por categoria",
                )

    if documento.titular_rut.is_empty:
        encontrado = re.search(_RE_RUT, texto, re.IGNORECASE)
        if encontrado:
            rut = parse_rut(encontrado.group(1))
            if rut:
                documento.titular_rut.set(
                    rut, CONF_MEDIA, encontrado.group(0), "RUT leido del encabezado"
                )

    if documento.fecha_atencion.is_empty and documento.fecha_emision.is_empty:
        encontrada = re.search(_RE_FECHA, texto, re.IGNORECASE)
        fecha = parse_date(encontrada.group(1)) if encontrada else None
        if fecha:
            campo = documento.fecha_atencion
            if TIPO_CATEGORIA.get(tipo) == CAT_BOLETAS or tipo == T_CERTIFICADO:
                campo = documento.fecha_emision
            campo.set(
                fecha.isoformat(), CONF_MEDIA, encontrada.group(0), "Fecha del encabezado"
            )

    if tipo in TIPOS_FICHA and documento.emisor_nombre.is_empty:
        prestador = prestador_de(documento, prestadores)
        if prestador:
            cabecera = _lineas(documento, 1)
            documento.emisor_nombre.set(
                prestador,
                CONF_BAJA if prestador.isupper() else CONF_MEDIA,
                cabecera[0] if cabecera else "",
                "Prestador identificado por el encabezado o la tabla de prestadores",
            )


def _descartar_rut_del_profesional(documento: Document) -> None:
    """Quita del titular el RUT que en realidad es del profesional que firma.

    En estos formularios el pie de pagina imprime "Dr. ... Rut: 11.111.111-1"
    para acreditar la firma. Cuando el bloque del nombre del paciente y el del
    pie se consolidan en un mismo documento, ese RUT queda como si fuera del
    paciente y produce un par nombre/RUT que no corresponde a nadie: el error
    mas peligroso que puede llegar al escrito.

    El dato no se borra: se deja anotado con la confianza baja, para que el
    revisor vea que existe y que no es del titular.
    """
    paciente = parse_rut(str(documento.titular_rut.value or ""))
    profesional = parse_rut(str(documento.profesional_rut.value or ""))
    if not (paciente and profesional and paciente == profesional):
        return
    documento.titular_rut.value = None
    documento.titular_rut.confidence = CONF_BAJA
    documento.titular_rut.note = (
        f"El RUT {paciente} que aparece impreso es el del profesional que firma; "
        "el RUT del paciente no es legible"
    )


def refinar(
    documento: Document,
    *,
    prestadores: tuple[Prestador, ...] | None = None,
) -> Document:
    """Normaliza el tipo del documento y completa sus datos faltantes.

    Es idempotente: aplicarlo dos veces deja el documento igual. Se puede
    ejecutar sobre un expediente ya calculado (sin repetir el OCR), que es lo
    que hace el comando ``ordenar``.
    """
    tipo = tipo_canonico(documento)
    if tipo != T_SIN_CLASIFICAR:
        _fijar_tipo(documento, tipo)
    _completar_desde_texto(documento, tipo, prestadores)
    # Va despues de completar: el propio texto del pie de pagina volveria a
    # introducir el RUT del profesional como RUT del paciente.
    _descartar_rut_del_profesional(documento)

    if tipo in {T_RECETA, T_RECETA_MEDICAMENTOS}:
        # El cuerpo de la receta esta manuscrito y el OCR no lo reconstruye; el
        # escrito no cita el medicamento, pero conviene dejarlo dicho.
        actual = fold(str(documento.observaciones.value or ""))
        if "manuscrit" not in actual:
            nota = "El medicamento prescrito esta manuscrito y no se transcribe"
            if documento.observaciones.is_empty:
                documento.observaciones.set(nota, CONF_MEDIA, "")
            else:
                documento.observaciones.value = f"{documento.observaciones.value}. {nota}"
    return documento


# ---------------------------------------------------------------------------
# Detalle especifico de cada categoria (lo que individualiza al documento)
# ---------------------------------------------------------------------------


def detalle_de(
    documento: Document,
    *,
    prestadores: tuple[Prestador, ...] | None = None,
) -> str:
    """Elementos que individualizan el documento segun su categoria.

    Devuelve una frase corta y citable en el escrito, con los elementos que el
    tipo de documento exige y que no tienen columna propia en la tabla.
    """
    tipo = tipo_canonico(documento)
    categoria = TIPO_CATEGORIA.get(tipo, CAT_OTROS)
    partes: list[str] = []

    if categoria == CAT_BONOS:
        receptor = str(_valor(documento, "profesional_nombre") or "").strip()
        if receptor:
            partes.append(f"prestador que atiende: {receptor}")
        copago = _valor(documento, "monto_copago")
        if isinstance(copago, int):
            partes.append(f"copago {format_clp(copago)}")

    elif categoria == CAT_BOLETAS:
        descripcion = [
            str(item.descripcion).strip()
            for item in documento.items
            if str(item.descripcion or "").strip()
        ]
        if descripcion:
            partes.append("detalle: " + " | ".join(descripcion[:3]))
        giro = str(_valor(documento, "emisor_giro") or "").strip()
        if giro:
            partes.append(f"giro: {giro}")

    elif categoria == CAT_RECETAS:
        profesional = str(_valor(documento, "profesional_nombre") or "").strip()
        if profesional:
            partes.append(f"firmada por: {profesional}")
        especialidad = str(_valor(documento, "profesional_especialidad") or "").strip()
        if especialidad:
            partes.append(especialidad)

    elif categoria == CAT_FICHAS:
        prestador = prestador_de(documento, prestadores)
        if prestador:
            partes.append(f"prestador: {prestador}")
        profesional = str(_valor(documento, "profesional_nombre") or "").strip()
        if profesional:
            partes.append(f"profesional: {profesional}")

    elif categoria == CAT_CERTIFICADOS:
        emisor = str(_valor(documento, "emisor_nombre") or "").strip() or prestador_de(
            documento, prestadores
        )
        if emisor:
            partes.append(f"emisor: {emisor}")

    return "; ".join(partes)


# ---------------------------------------------------------------------------
# Nombres de archivo y de carpeta
# ---------------------------------------------------------------------------

_CARACTERES_INVALIDOS = re.compile(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ .,+-]")


def limpiar_nombre(texto: str, maximo: int = 120) -> str:
    """Deja un texto apto para nombre de archivo en cualquier sistema."""
    base = " ".join(str(texto or "").split())
    base = _CARACTERES_INVALIDOS.sub(" ", base)
    base = " ".join(base.split()).strip(" .-")
    return base[:maximo].strip(" .-")


def nombre_archivo(
    numero: int,
    tipo: str,
    fecha: str,
    titular: str = "",
    folio: str = "",
    *,
    maximo: int = 150,
) -> str:
    """Nombre del PDF individual: numero, fecha, tipo, titular y folio."""
    partes = [f"{numero:03d}", fecha, tipo, titular]
    if folio:
        partes.append(f"folio {folio}")
    nombre = limpiar_nombre(" ".join(parte for parte in partes if parte), maximo)
    return f"{nombre}.pdf"


def carpeta_de(prestador: str) -> str:
    """Nombre de carpeta para las fichas de un prestador."""
    return limpiar_nombre(prestador or SIN_PRESTADOR, 60).upper() or "SIN PRESTADOR"


def fecha_texto(documento: Document) -> str:
    """Fecha del documento en formato dd-mm-aaaa (vacia si no se pudo leer)."""
    from .individualizacion import fecha_de

    return format_date_cl(fecha_de(documento))
