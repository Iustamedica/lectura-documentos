"""Extractores especializados por familia documental.

El registro `EXTRACTORS` mapea la familia detectada por `classify` al extractor
correspondiente. Cuando la familia es desconocida o el texto esta muy degradado
se aplica `extract_generic`, que busca RUT, fechas y montos por proximidad.
"""

from __future__ import annotations

import re

from ..layout import Block
from ..models import CONF_ALTA, CONF_BAJA, CONF_MEDIA, Document
from ..normalizers import (
    clean_name,
    fold,
    is_person_rut,
    looks_like_form_label,
    looks_like_person_name,
    names_overlap,
    parse_clp,
    parse_date,
    parse_rut,
    plausible_person_name,
    roman_letters_to_digits,
    rut_is_prestador,
)
from .fonasa import extract_fonasa
from .sii import extract_sii

# --------------------------------------------------------------------------
# Receta optica
# --------------------------------------------------------------------------


def extract_optica(block: Block, doc: Document) -> Document:
    """Receta optica: titular RUT, fecha, profesional y formulario de lentes."""
    lines = block.lines
    text = block.text

    doc.familia = "receta_optica"
    doc.tipo_documento.set("Receta optica", CONF_MEDIA, "RECETA OPTICA")

    for line in lines:
        if re.search(r"nombre|paciente", fold(line.text)):
            rut = parse_rut(line.text)
            if rut and is_person_rut(rut) and not rut_is_prestador(line.text, rut):
                doc.titular_rut.set(rut, CONF_MEDIA, line.text)
            nombre = re.split(r"r\.?\s*u\.?t", line.text, flags=re.IGNORECASE)[0]
            nombre = clean_name(re.sub(r"(?i)^\s*(nombre|paciente)\s*:?", "", nombre))
            if plausible_person_name(nombre):
                doc.titular_nombre.set(nombre.upper(), CONF_MEDIA, line.text)
            break

    fecha = parse_date(text)
    if fecha:
        doc.fecha_emision.set(fecha.isoformat(), CONF_MEDIA, fecha.strftime("%d-%m-%Y"))

    # Firma del profesional: linea con "Tecnologo Medico" u "Oftalmologo".
    for index, line in enumerate(lines):
        if re.search(r"(tecnolog|oftalmolog|opometr|optometr)", fold(line.text)):
            if index > 0:
                prev = clean_name(lines[index - 1].text)
                if looks_like_person_name(prev):
                    doc.profesional_nombre.set(prev.upper(), CONF_BAJA, lines[index - 1].text)
            doc.profesional_especialidad.set(
                clean_name(line.text).upper(), CONF_BAJA, line.text
            )
            break

    # Detalle optico (ESF/CIL/EJE/DP/ADD)
    detalles = [
        clean_name(line.text) for line in lines
        if re.search(r"\b(esf|cil|eje|dp|add)\b", fold(line.text))
    ]
    if detalles:
        doc.observaciones.set(" | ".join(detalles), CONF_MEDIA, detalles[0])
    return doc


def extract_optica_boleta(block: Block, doc: Document) -> Document:
    """Boleta de optica: se comporta como boleta SII con giro optica."""
    doc = extract_sii(block, doc)
    doc.familia = "boleta_sii"
    return doc


# --------------------------------------------------------------------------
# Ticket de farmacia
# --------------------------------------------------------------------------


def extract_farmacia(block: Block, doc: Document) -> Document:
    """Ticket o boleta de farmacia.

    El OCR de estos tickets suele ser el peor del expediente (papel termico,
    letra pequena), por lo que solo se confian los datos con patron fuerte y
    todo lo demas queda marcado para revision.
    """
    lines = block.lines
    text = block.text

    doc.familia = "ticket_farmacia"
    doc.tipo_documento.set("Boleta de farmacia", CONF_MEDIA, "BOLETA")

    for line in lines[:3]:
        folded = fold(line.text)
        for cadena, nombre in (
            ("salcobrand", "SALCOBRAND"),
            ("cruz verde", "FARMACIAS CRUZ VERDE"),
            ("ahumada", "FARMACIAS AHUMADA"),
            ("simi", "FARMACIA DR. SIMI"),
        ):
            if cadena in folded:
                doc.emisor_nombre.set(nombre, CONF_MEDIA, line.text)
                break
        if not doc.emisor_nombre.is_empty:
            break

    folio = re.search(r"boleta\s*(?:electr[oó]nica)?\s*n?[°ºo.]*\s*(\d{6,12})", fold(text))
    if folio is None:
        folio = re.search(r"nro\.?\s*:?\s*(\d{6,12})", fold(text))
    if folio:
        doc.folio.set(folio.group(1), CONF_BAJA, folio.group(0), "Folio detectado en ticket")

    for line in lines:
        if re.search(r"fecha", fold(line.text)):
            fecha = parse_date(line.text)
            if fecha:
                doc.fecha_emision.set(fecha.isoformat(), CONF_MEDIA, line.text)
                break

    # Titular: "Sr(a).: NOMBRE Rut 12.345.678-5" (el nombre puede venir cortado)
    for line in lines:
        folded = fold(line.text)
        if re.search(r"sr\s*\(?a?\)?", folded) or "rut" in folded:
            rut = parse_rut(line.text)
            if rut:
                doc.titular_rut.set(rut, CONF_MEDIA, line.text)
            head = re.split(r"(?i)rut", line.text)[0]
            head = re.sub(r"(?i)^\s*sr\s*\(?a?\)?\s*[:.]?", "", head)
            candidate = clean_name(head)
            if candidate:
                doc.titular_nombre.set(candidate.upper(), CONF_BAJA, line.text,
                                       "Nombre posiblemente truncado en el original")

    total = None
    for line in lines:
        if re.search(r"^total|total\s*(?:a\s*pagar)?\s*\$", fold(line.text)):
            total = parse_clp(re.search(r"\$?\s*[\d.]{4,}", line.text).group(0)) if re.search(
                r"\$?\s*[\d.]{4,}", line.text
            ) else None
            if total:
                doc.monto_total.set(total, CONF_MEDIA, line.text)
                break

    items = []
    for line in lines:
        folded = fold(line.text)
        if not re.search(r"(comp|mg|ml|caps|tab|caja|vitamin|sachet|crema)", folded):
            continue
        items.append(clean_name(line.text))
    if items:
        doc.observaciones.set("Productos: " + " | ".join(items[:6]), CONF_BAJA, items[0])
    return doc


# --------------------------------------------------------------------------
# Documentos clinicos y contractuales
# --------------------------------------------------------------------------

MOTIVO_RUT_NO_LEGIBLE = (
    "El RUT impreso en el documento corresponde al centro medico o al profesional; "
    "el RUT del paciente no es legible (revisar el original)"
)


# Marcadores de direccion: si aparecen tras un "Rut:", el texto no es un nombre.
_MARCAS_DIRECCION = (
    " cerro ", " av ", " avenida ", " calle ", " of ", " oficina ", " piso ",
    " local ", " santiago ", " condes ", " providencia ", " region ",
)


def _es_direccion(texto: str) -> bool:
    """True si el texto parece una direccion o ciudad y no un nombre."""
    plegado = f" {fold(texto)} "
    if any(marca in plegado for marca in _MARCAS_DIRECCION):
        return True
    return bool(re.search(r"\b(?:av|avda|calle|of|piso|local)\.?\b", plegado))


def _rut_de_medico(rut: str, texto: str) -> bool:
    """True si el RUT aparece asociado al profesional que firma el documento.

    En las recetas oftalmologicas el RUT del profesional se imprime suelto
    ("Rp. RUT: 11.111.111-1") o en el pie del recibo ("Rut: 11.111.111-1
    Pablo Fuentes D.", dos lineas antes de "clinica@ejemplo.cl"). Se
    considera del medico cuando cerca del RUT aparece un tratamiento ("Dr.",
    "Dra.", "Oftalmologo") o cuando la linea lo presenta con la etiqueta
    "Rut:"/"Rp." junto a un nombre de persona que no es del paciente.
    """
    partes = [p.strip() for p in texto.splitlines() if p.strip()]
    for indice, linea in enumerate(partes):
        if rut not in (parse_rut(linea) or ""):
            continue
        # Ventana amplia: el OCR separa el nombre del medico del RUT por un
        # renglon de direccion ("Cerro Colorado 5030 Of. 104...").
        contexto = fold(" ".join(partes[indice : indice + 5]))
        if re.search(r"\b(dr|dra|doctor|doctora|medico|oftalmologo)\b", contexto):
            return True
        if re.search(r"\b(?:rp|rut)\.?\s*:", fold(linea)):
            resto = re.split(r"(?i)\br(?:\.?\s*u\.?\s*t\.?|p\.?)\s*:", linea)[-1]
            resto = clean_name(re.sub(r"(?i)\d[\d.\s]*-?[\dkK]\b", " ", resto))
            # Estructura de nombre, no contenido: el OCR de estos pies de
            # pagina produce "PabbloFuentes D.", que no calza con ningun nombre
            # conocido pero sigue siendo un nombre y no una direccion. Se
            # descartan las direcciones y ciudades aunque parezcan nombres.
            if looks_like_person_name(resto) and not _es_direccion(resto):
                return True
    return False


def extract_clinico(
    block: Block, doc: Document, nombres_conocidos: list[str] | None = None
) -> Document:
    """Documento clinico generico: informe, certificado, orden de examen.

    El nombre del paciente suele estar escrito a mano y el RUT impreso en estos
    formularios es el del centro medico, no el del paciente, por lo que:
      - solo se acepta como RUT del titular un RUT de persona natural que no
        este etiquetado como prestador/establecimiento;
      - si hay una etiqueta "Nombre:" pero el texto no es un nombre legible, el
        paciente se intenta reconocer cotejando con los nombres del expediente y
        queda marcado para verificacion.
    """
    lines = block.lines
    text = block.text

    doc.familia = "documento_clinico"
    titulo = next(
        (
            clean_name(line.text)
            for line in lines[:6]
            if re.search(
                r"(informe|certificado|orden|solicitud|receta|atencion|epicrisis|examenes)",
                fold(line.text),
            )
        ),
        "",
    )
    doc.tipo_documento.set(
        titulo.upper() if titulo else "Documento clinico", CONF_MEDIA, titulo
    )
    if titulo:
        doc.titulo = titulo.upper()

    rut_paciente = None
    etiqueta_nombre = ""
    candidatos: list[tuple[str, str]] = []
    for line in lines[:14]:
        folded = fold(line.text)
        rut_linea = parse_rut(line.text)
        # Un RUT en la misma linea que "Dr."/"Rut:" es del profesional, no del
        # paciente (estos formularios imprimen el RUT del medico junto al nombre).
        es_linea_medico = bool(re.search(r"(dr\.?|dra\.?|medico|rut\s*:\s*$)", folded))
        if rut_linea and is_person_rut(rut_linea):
            candidatos.append((rut_linea, line.text))
        if (
            rut_linea
            and is_person_rut(rut_linea)
            and not rut_is_prestador(line.text, rut_linea)
            and not es_linea_medico
        ):
            rut_paciente = rut_paciente or rut_linea
        match = re.search(r"(?:nombre|paciente)\s*:", folded)
        if match and not etiqueta_nombre:
            # Se toma solo lo anterior a "R.U.T." para no arrastrar el RUT ajeno.
            previo = re.split(r"(?i)r\.?\s*u\.?\s*t\b", line.text)[0]
            etiqueta_nombre = re.split(r"(?i)nombre\s*:|paciente\s*:", previo)[-1]
            if doc.titular_nombre.is_empty:
                candidate = clean_name(etiqueta_nombre)
                if plausible_person_name(candidate):
                    doc.titular_nombre.set(candidate.upper(), CONF_MEDIA, line.text)

    # El RUT impreso puede ser el del profesional aunque no este en la misma
    # linea que "Dr.": en "Rp. RUT: 11.111.111-1 ... Dr. Pablo Fuentes D." el
    # RUT es del medico que firma, no del paciente. En ese caso no se registra
    # como RUT del titular; en cambio se guarda como RUT del profesional.
    if rut_paciente and _rut_de_medico(rut_paciente, text):
        if doc.profesional_rut.is_empty:
            doc.profesional_rut.set(rut_paciente, CONF_MEDIA, rut_paciente)
        rut_paciente = None

    if rut_paciente:
        doc.titular_rut.set(rut_paciente, CONF_MEDIA, rut_paciente)
    elif doc.titular_rut.is_empty:
        doc.titular_rut.mark_missing(MOTIVO_RUT_NO_LEGIBLE)

    if doc.profesional_rut.is_empty:
        for rut_candidato, linea in candidatos:
            if _rut_de_medico(rut_candidato, linea) or _rut_de_medico(rut_candidato, text):
                doc.profesional_rut.set(rut_candidato, CONF_MEDIA, linea)
                break

    # Paciente manuscrito ilegible: se reconoce por los nombres del expediente.
    if doc.titular_nombre.is_empty and nombres_conocidos:
        for nombre in nombres_conocidos:
            if names_overlap(nombre, etiqueta_nombre, min_shared=1) or names_overlap(
                nombre, text, min_shared=1
            ):
                doc.titular_nombre.set(
                    nombre.upper(),
                    CONF_BAJA,
                    etiqueta_nombre.strip() or "texto del documento",
                    "Nombre manuscrito ilegible: titular inferido por otros documentos "
                    "del expediente, confirmar contra el original",
                )
                break

    for line in lines:
        if re.search(r"fecha", fold(line.text)):
            fecha = parse_date(roman_letters_to_digits(line.text))
            if fecha:
                doc.fecha_atencion.set(fecha.isoformat(), CONF_MEDIA, line.text)
                doc.fecha_emision.set(fecha.isoformat(), CONF_MEDIA, line.text)
                break
    if doc.fecha_emision.is_empty:
        fecha = parse_date(roman_letters_to_digits(text))
        if fecha:
            doc.fecha_emision.set(fecha.isoformat(), CONF_BAJA, fecha.strftime("%d-%m-%Y"))

    # Profesional tratante: RUT impreso con etiqueta "Dr." o "Rut del medico".
    for line in lines:
        if re.search(r"(dr\.?|dra\.?|medico|profesional)", fold(line.text)):
            rut_medico = parse_rut(line.text)
            if rut_medico and doc.profesional_rut.is_empty:
                doc.profesional_rut.set(rut_medico, CONF_MEDIA, line.text)
            nombre_medico = clean_name(re.split(r"(?i)r\.?\s*u\.?\s*t", line.text)[0])
            nombre_medico = clean_name(re.sub(r"(?i)\b(?:dr|dra)\.?\s*", "", nombre_medico))
            if (
                doc.profesional_nombre.is_empty
                and looks_like_person_name(nombre_medico)
                and len(nombre_medico.split()) <= 5
            ):
                doc.profesional_nombre.set(nombre_medico.upper(), CONF_BAJA, line.text)
            break

    diagnostico = re.search(r"diagn[oó]stico\s*:?\s*([^\n]{3,120})", text, re.IGNORECASE)
    if diagnostico and clean_name(diagnostico.group(1)):
        doc.diagnostico.set(clean_name(diagnostico.group(1)), CONF_MEDIA, diagnostico.group(0))
    return doc


def extract_pagare(block: Block, doc: Document) -> Document:
    """Pagare o aviso de vencimiento: deudor, monto y fechas."""
    lines = block.lines
    text = block.text

    doc.familia = "pagare"
    doc.tipo_documento.set("Pagare", CONF_ALTA, "PAGARE")

    folio = re.search(r"pag[ae]r[eé]\s*n\s*[°ºo.]*\s*:?\s*(\d{4,12})", text, re.IGNORECASE)
    if folio:
        doc.folio.set(folio.group(1), CONF_MEDIA, folio.group(0))

    # Beneficiario de la orden de pago (emisor del documento).
    emisor = re.search(
        r"a\s*la\s*orden\s*de\s*([A-ZÁÉÍÓÚÑ0-9 .,&'-]{5,70})", text, re.IGNORECASE
    )
    if emisor:
        doc.emisor_nombre.set(clean_name(emisor.group(1)).upper(), CONF_MEDIA, emisor.group(0))
    emisor_rut = parse_rut(text)
    if emisor_rut:
        doc.emisor_rut.set(emisor_rut, CONF_MEDIA, emisor_rut)

    monto = re.search(
        r"(?:capital\s*total\s*adeudado|monto|capital|total|saldo)[^\d$]{0,20}\$?\s*([\d.]{4,})",
        text,
        re.IGNORECASE,
    )
    if monto:
        doc.monto_total.set(parse_clp(monto.group(1)), CONF_MEDIA, monto.group(0))
    return doc

    for line in lines:
        folded = fold(line.text)
        if re.search(r"(deudor|nombre|deb(o|e)\s*y\s*pagar)", folded):
            rut = parse_rut(line.text)
            if rut and doc.titular_rut.is_empty:
                doc.titular_rut.set(rut, CONF_MEDIA, line.text)
            candidate = clean_name(re.split(r"(?i)r\.?\s*u\.?t", line.text)[0])
            if doc.titular_nombre.is_empty and looks_like_person_name(candidate):
                doc.titular_nombre.set(candidate.upper(), CONF_MEDIA, line.text)

    for line in lines:
        folded = fold(line.text)
        if re.search(r"(vence|vencimiento)", folded):
            fecha = parse_date(line.text)
            if fecha:
                doc.fecha_vencimiento.set(fecha.isoformat(), CONF_MEDIA, line.text)
        elif re.search(r"fecha", folded) and doc.fecha_emision.is_empty:
            fecha = parse_date(line.text)
            if fecha:
                doc.fecha_emision.set(fecha.isoformat(), CONF_MEDIA, line.text)

    monto = re.search(
        r"(?:monto|capital|total|saldo)[^\d$]{0,20}\$?\s*([\d.]{4,})", text, re.IGNORECASE
    )
    if monto:
        doc.monto_total.set(parse_clp(monto.group(1)), CONF_MEDIA, monto.group(0))
    return doc


# --------------------------------------------------------------------------
# Respaldo generico y registro
# --------------------------------------------------------------------------


def extract_generic(block: Block, doc: Document) -> Document:
    """Extraccion de respaldo: RUT, fechas y montos por proximidad.

    Se usa cuando la familia no se reconoce. Sirve para no perder documentos:
    el informe los muestra con advertencia explicita para revision manual.
    """
    lines = block.lines
    text = block.text

    if not doc.tipo_documento.value:
        doc.tipo_documento.set(
            "Documento sin clasificar", CONF_BAJA, lines[0].text if lines else ""
        )
    if not doc.titulo and lines:
        doc.titulo = clean_name(lines[0].text)[:80]

    etiquetas = r"(nombre|paciente|beneficiari|afiliad|senor|sr\s*\(?a?\)?|cliente|titular)"
    for line in lines:
        if not re.search(etiquetas, fold(line.text)):
            continue
        rut = parse_rut(line.text)
        if (
            rut
            and doc.titular_rut.is_empty
            and is_person_rut(rut)
            and not rut_is_prestador(line.text, rut)
        ):
            doc.titular_rut.set(rut, CONF_MEDIA, line.text)
        head = re.split(r"(?i)(r\.?\s*u\.?\s*t|:)", line.text)[-1]
        candidate = clean_name(head)
        if doc.titular_nombre.is_empty and plausible_person_name(candidate):
            doc.titular_nombre.set(candidate.upper(), CONF_BAJA, line.text)

    if doc.titular_rut.is_empty:
        for line in lines[:10]:
            rut = parse_rut(line.text)
            if rut and is_person_rut(rut) and not rut_is_prestador(line.text, rut):
                doc.titular_rut.set(
                    rut, CONF_BAJA, line.text, "RUT sin etiqueta: verificar titular"
                )
                break

    if doc.fecha_emision.is_empty:
        fecha = parse_date(roman_letters_to_digits(text))
        if fecha:
            doc.fecha_emision.set(fecha.isoformat(), CONF_BAJA, fecha.strftime("%d-%m-%Y"))

    if doc.monto_total.is_empty:
        candidatos: list[tuple[int, str]] = []
        for line in lines:
            if not re.search(r"(total|a\s*pagar|monto|valor)", fold(line.text)):
                continue
            valores = re.findall(r"\d{1,3}(?:\.\d{3})+", line.text)
            if valores:
                valor = parse_clp(valores[-1])
                if valor:
                    candidatos.append((valor, line.text))
        if candidatos:
            valor, raw = max(candidatos, key=lambda pair: pair[0])
            doc.monto_total.set(valor, CONF_BAJA, raw, "Monto inferido: verificar")
    return doc


EXTRACTORS = {
    "bono_fonasa": extract_fonasa,
    "boleta_sii": extract_sii,
    "ticket_farmacia": extract_farmacia,
    "documento_clinico": extract_clinico,
    "pagare": extract_pagare,
    "receta_optica": extract_optica,
    "resultado_laboratorio": extract_clinico,
    "desconocido": extract_generic,
}


def get_extractor(familia: str):
    """Devuelve el extractor para una familia (generico si no hay uno propio)."""
    return EXTRACTORS.get(familia, extract_generic)


# --------------------------------------------------------------------------
# Recetas manuscritas del oftalmologo
# --------------------------------------------------------------------------


def extract_receta_manuscrita(
    block: Block, doc: Document, nombres_conocidos: list[str] | None = None
) -> Document:
    """Receta del oftalmologo: RUT del profesional impreso + paciente manuscrito.

    En estas recetas el RUT impreso corresponde al medico, no al paciente. El
    nombre del paciente esta escrito a mano y el OCR lo degrada mucho
    ("T/Aont Nel Loneyal Anost"), por lo que:
      - el RUT del medico se registra como `profesional_rut`;
      - el paciente se identifica cotejando con los nombres ya conocidos del
        expediente (puntaje de palabras en comun), nunca inventando un nombre.
    """
    lines = block.lines
    text = block.text

    doc.familia = "receta_optica"
    doc.tipo_documento.set("Receta medica oftalmologica", CONF_MEDIA, "Rp.")

    rut_medico = parse_rut(text)
    if rut_medico:
        doc.profesional_rut.set(rut_medico, CONF_ALTA, rut_medico)

    for line in lines[:6]:
        folded = fold(line.text)
        if "oftalmolog" in folded or "dr." in folded or "doctor" in folded:
            candidate = clean_name(re.split(r"(?i)r\.?\s*u\.?t|icm", line.text)[0])
            candidate = re.sub(r"(?i)\b(?:dr|dra)\.?\s*", "", candidate)
            candidate = clean_name(candidate)
            if looks_like_person_name(candidate):
                doc.profesional_nombre.set(candidate.upper(), CONF_BAJA, line.text)
                doc.profesional_especialidad.set("OFTALMOLOGIA", CONF_MEDIA, line.text)
                break

    fecha = parse_date(roman_letters_to_digits(text))
    if fecha:
        doc.fecha_emision.set(fecha.isoformat(), CONF_BAJA, fecha.strftime("%d-%m-%Y"))

    mejor: tuple[float, str] | None = None
    for nombre in nombres_conocidos or []:
        if names_overlap(nombre, text, min_shared=2):
            palabras = set(re.findall(r"[a-zñ]{3,}", fold(nombre)))
            puntaje = len(palabras) + len(palabras & set(re.findall(r"[a-zñ]{3,}", fold(text))))
            if mejor is None or puntaje > mejor[0]:
                mejor = (float(puntaje), nombre)
    if mejor:
        doc.titular_nombre.set(
            mejor[1].upper(),
            CONF_BAJA,
            "Nombre manuscrito ilegible en el OCR",
            "Titular inferido por coincidencia con otros documentos del expediente: "
            "confirmar contra el original",
        )
    else:
        doc.observaciones.set(
            "Paciente manuscrito ilegible: revisar el original", CONF_BAJA, ""
        )
    return doc



