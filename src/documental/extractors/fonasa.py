"""Extractor para bonos de atencion FONASA.

Estructura tipica (4 cuadrantes):

    BONO DE ATENCION AMBULATORIA          FOLIO NNNNNNN
    Rut Beneficiario 12.345.678-9         Nombre BENEFICIARIO
    Rut Prestador ...                     Nombre PRESTADOR
    Tipo de Prestacion / Codigo / Fecha Atencion / Hora
    Prestaciones:  Valor / Bonificacion / Aporte Copago
    Total a Pagar: $
"""

from __future__ import annotations

import re

from ..layout import Block, Line, line_value_after
from ..models import CONF_ALTA, CONF_BAJA, CONF_MEDIA, Document
from ..normalizers import (
    clean_name,
    first_match,
    fold,
    format_clp,
    is_person_rut,
    looks_like_form_label,
    looks_like_person_name,
    parse_clp,
    parse_date,
    parse_rut,
    parse_time,
    rut_is_prestador,
    squeeze,
)

_NAME_LABELS = (
    r"beneficiari[oa]\s*\(?a?\)?\s*:",
    r"afiliad[oa]\s*\(?a?\)?\s*:",
    r"paciente\s*:",
    r"(?:nombre|nombres)\s*(?:completo)?s?\s*:?",
)

_RUT_LABELS = (
    r"afiliad[oa]\s*\(?a?\)?\s*:",
    r"beneficiari[oa]\s*\(?a?\)?\s*:",
    r"rut\s*(?:beneficiari[oa]|paciente|afiliad[oa]|titular)",
    r"rut\s*:",
)

_TOTAL_LABELS = (
    r"a\s*pagar",
    r"total\s*a\s*pagar",
    r"monto\s*a\s*pagar",
    r"valor\s*a\s*pagar",
    r"total\s*bono",
    r"total\s*:",
)

_COPAGO_LABELS = (
    r"copago",
    r"a\s*pagar",
    r"(?:aporte|monto)\s*copago",
)

_BONIF_LABELS = (
    r"bonificaci[oó]n\s*(?:financiador)?\s*\$?\s*[\d.]+.*?\$?\s*([\d.]{3,})",
    r"bonificaci[oó]n",
    r"aporte\s*fonasa",
)

_BRUTO_LABELS = (
    r"valor\s*\$",
    r"valor\s*prestaci[oó]n",
    r"valor\s*bruto",
)

_BENEFICIARIO_LINE = re.compile(
    r"beneficiari[oa]\s*\(?a?\)?\s*:\s*(?:\d[\d.\s-]{5,12})\s+(.+)", re.IGNORECASE
)


def _money_near(lines: list[Line], labels: tuple[str, ...]) -> tuple[int | None, str]:
    """Busca un monto en la linea de la etiqueta o en la inmediatamente siguiente.

    Se usa el texto que realmente matcheo el patron en la linea plegada, no una
    reconstruccion del regex: reconstruir la etiqueta dejaba "\\s*" convertido en
    "s*" y el monto terminaba tomandose del primer numero de la linea.
    """
    for index, line in enumerate(lines):
        folded = fold(line.text)
        for label in labels:
            match = re.search(label, folded)
            if not match:
                continue
            value = parse_clp(line_value_after(line, match.group(0)) or line.text)
            if value:
                return value, line.text
            if index + 1 < len(lines):
                value = parse_clp(lines[index + 1].text)
                if value:
                    return value, f"{line.text} {lines[index + 1].text}"
    return None, ""


def _find_name(lines: list[Line]) -> tuple[str, str, str]:
    """Devuelve (nombre, confianza, texto crudo) del titular.

    En FONASA el nombre aparece como "Beneficiario(a): 00012345678-5 APELLIDOS
    NOMBRES / Edad:71", por lo que se recorta el RUT y la cola "/ Edad".
    Solo se aceptan lineas con etiqueta explicita: tomar "la primera linea en
    mayusculas" confundia el nombre del prestador con el del paciente.
    """
    candidatos: list[tuple[str, str, str]] = []
    for line in lines:
        match = _BENEFICIARIO_LINE.search(line.text)
        if match:
            candidate = clean_name(re.split(r"[/|]", match.group(1))[0])
            if looks_like_person_name(candidate) and not looks_like_form_label(candidate):
                candidatos.append((candidate.upper(), CONF_ALTA, line.text))

    for line in lines:
        folded = fold(line.text)
        for label in _NAME_LABELS:
            match = re.search(label, folded)
            if not match:
                continue
            remainder = line_value_after(line, match.group(0))
            remainder = re.split(r"[/|]", remainder)[0]
            remainder = re.sub(r"^\d[\d.\s-]{5,12}\s+", "", remainder)
            candidate = clean_name(remainder)
            if looks_like_person_name(candidate) and not looks_like_form_label(candidate):
                confianza = CONF_ALTA if "beneficiari" in label else CONF_MEDIA
                candidatos.append((candidate.upper(), confianza, line.text))

    if not candidatos:
        return "", "", ""
    # El primero es el de la linea "Beneficiario(a):", que es el orden correcto.
    return candidatos[0]





def extract_fonasa(block: Block, doc: Document) -> Document:
    """Completa los campos de un bono FONASA (o de un programa de salud FONASA)."""
    lines = block.lines
    text = block.text

    if re.search(r"programa\s*de\s*atenci[oó]n", fold(text)):
        return _extract_programa(block, doc)

    doc.familia = "bono_fonasa"
    doc.titulo = "Bono FONASA"
    doc.tipo_documento.set("Bono de atencion FONASA", CONF_ALTA, "BONO DE ATENCION")

    folio = first_match(
        (
            r"bono\s*de\s*atenci[oó]n\s*ambulatoria\s+(\d{5,12})",
            r"folio\s*(?:n[°ºo.]*)?\s*:?\s*(\d{5,12})",
            r"n[°ºo.]*\s*bono\s*:?\s*(\d{5,12})",
        ),
        text,
    )
    if folio:
        doc.folio.set(folio, CONF_ALTA, folio)
    else:
        # En los bonos que vienen rotados (la hoja apaisada se escanea girada) el
        # folio queda impreso en el borde, lejos de la etiqueta "FOLIO": el OCR
        # lo entrega como primera palabra del bloque. Los folios FONASA tienen 9
        # digitos; se aceptan 9 a 12 sin separadores y con confianza media para
        # que se pueda contrastar con el original.
        inicial = first_match((r"(?m)^\s*(\d{9,12})(?![\dK-])",), text)
        if inicial:
            doc.folio.set(
                inicial, CONF_MEDIA, text[:40].strip(), "numero al inicio del documento"
            )

    edad = first_match((r"edad\s*:?\s*(\d{1,3})",), text)
    if edad and int(edad) < 120:
        doc.titular_edad.set(int(edad), CONF_MEDIA, edad)

    direccion = first_match((r"direcci[oó]n\s*:?\s*([^\n]{4,80})",), text)
    if direccion:
        doc.titular_direccion.set(clean_name(direccion).upper(), CONF_MEDIA, direccion)

    prevision = first_match((r"plan\s*grupo\s*:?\s*([A-D])",), text)
    if prevision:
        doc.titular_prevision.set(f"FONASA tramo {prevision.upper()}", CONF_MEDIA, prevision)

    # RUT del beneficiario. Se exige que sea RUT de persona natural y que no
    # este asociado a prestador/profesional; si no, queda vacio para revision.
    for line in lines:
        if any(re.search(label, fold(line.text)) for label in _RUT_LABELS):
            rut = parse_rut(line.text)
            if rut and is_person_rut(rut) and not rut_is_prestador(line.text, rut):
                doc.titular_rut.set(rut, CONF_ALTA, line.text)
                break
    if doc.titular_rut.is_empty:
        for line in lines[:10]:
            rut = parse_rut(line.text)
            if rut and is_person_rut(rut) and not rut_is_prestador(line.text, rut):
                doc.titular_rut.set(
                    rut, CONF_MEDIA, line.text, "RUT sin etiqueta reconocible"
                )
                break

    nombre, confianza, raw = _find_name(lines)
    if nombre:
        doc.titular_nombre.set(nombre, confianza, raw)

    # Prestador
    prestador = first_match(
        (r"nombre\s*(?:del\s*)?prestador\s*:?\s*([A-Za-zÁÉÍÓÚÑ0-9 .,&'-]{4,60})",),
        text,
    )
    if prestador:
        doc.emisor_nombre.set(clean_name(prestador).upper(), CONF_MEDIA, prestador)
    for line in lines:
        if re.search(r"rut\s*(?:del\s*)?prestador", fold(line.text)):
            prestador_rut = parse_rut(line.text)
            if prestador_rut:
                doc.emisor_rut.set(prestador_rut, CONF_ALTA, line.text)
            break

    # Fechas
    for line in lines:
        folded = fold(line.text)
        if "hora" in folded and doc.hora.is_empty:
            hora = parse_time(line.text)
            if hora:
                doc.hora.set(hora, CONF_MEDIA, line.text)
        if "fecha" in folded and ("atencion" in folded or "emision" in folded):
            fecha = parse_date(line.text)
            if fecha:
                doc.fecha_atencion.set(fecha.isoformat(), CONF_MEDIA, line.text)
                doc.fecha_emision.set(fecha.isoformat(), CONF_MEDIA, line.text)
                hora = parse_time(line.text)
                if hora and doc.hora.is_empty:
                    doc.hora.set(hora, CONF_MEDIA, line.text)
            continue
    if doc.fecha_atencion.is_empty:
        for line in lines:
            if "fecha" in fold(line.text):
                fecha = parse_date(line.text)
                if fecha:
                    doc.fecha_atencion.set(fecha.isoformat(), CONF_BAJA, line.text)
                    doc.fecha_emision.set(fecha.isoformat(), CONF_BAJA, line.text)
                    break
    if doc.fecha_emision.is_empty and not doc.fecha_atencion.is_empty:
        doc.fecha_emision.set(
            doc.fecha_atencion.value,
            CONF_MEDIA,
            doc.fecha_atencion.raw,
            "Fecha de emision asumida igual a la de atencion",
        )

    # Montos
    total, raw_total = _money_near(lines, _TOTAL_LABELS)
    if total is not None:
        doc.monto_total.set(total, CONF_ALTA, raw_total)
    copago, raw_copago = _money_near(lines, _COPAGO_LABELS)
    if copago is not None:
        doc.monto_copago.set(copago, CONF_MEDIA, raw_copago)
    bonif, raw_bonif = _money_near(lines, _BONIF_LABELS)
    if bonif is not None:
        doc.monto_bonificacion.set(bonif, CONF_MEDIA, raw_bonif)
    bruto, raw_bruto = _money_near(lines, _BRUTO_LABELS)
    if bruto is not None:
        doc.monto_bruto.set(bruto, CONF_MEDIA, raw_bruto)

    if (
        doc.monto_bruto.value is not None
        and doc.monto_bonificacion.value is not None
        and doc.monto_copago.value is not None
    ):
        suma = doc.monto_bonificacion.value + doc.monto_copago.value
        if abs(suma - doc.monto_bruto.value) > 1:
            doc.monto_bruto.confidence = CONF_BAJA
            doc.monto_bruto.note = (
                f"Inconsistencia: bonificacion {format_clp(doc.monto_bonificacion.value)} + "
                f"copago {format_clp(doc.monto_copago.value)} != bruto "
                f"{format_clp(doc.monto_bruto.value)}"
            )
    elif doc.monto_total.value is not None and doc.monto_bonificacion.value is not None:
        doc.monto_bruto.set(
            doc.monto_total.value + doc.monto_bonificacion.value,
            CONF_BAJA,
            "Calculado como total + bonificacion",
        )

    _extract_prestaciones(lines, doc)
    return doc


def _extract_prestaciones(lines: list[Line], doc: Document) -> None:
    """Extrae lineas de prestaciones con sus montos."""
    from ..models import LineItem

    for line in lines:
        text = squeeze(line.text)
        if not re.search(r"\d{1,3}(?:\.\d{3})+|\b\d{4,}\b", text):
            continue
        if not re.search(r"[A-Za-zÁÉÍÓÚÑ]{4,}", text):
            continue
        if any(word in fold(text) for word in ("total", "folio", "rut", "fecha", "bono")):
            continue
        amounts = re.findall(r"\d{1,3}(?:\.\d{3})+|\b\d{4,}\b", text)
        descripcion = re.split(r"\s{2,}|\d{1,3}(?:\.\d{3})+", text, maxsplit=1)[0]
        item = LineItem(
            descripcion=clean_name(descripcion),
            raw=text,
            confidence=CONF_MEDIA if line.score >= 0.8 else CONF_BAJA,
        )
        if amounts:
            item.total = parse_clp(amounts[-1])
        if len(amounts) >= 2:
            item.valor_unitario = parse_clp(amounts[-2])
        if len(amounts) >= 3:
            item.bonificacion = parse_clp(amounts[-3])
        codigo = re.search(r"\b(\d{5,8})\b", descripcion)
        if codigo:
            item.codigo = codigo.group(1)
        doc.items.append(item)


def _extract_programa(block: Block, doc: Document) -> Document:
    """Programa de Atencion de Salud FONASA (lentes, tratamientos, etc.).

    Formato compacto en una sola linea, con etiquetas del tipo:

        PROGRAMA DE ATENCION DE SALUD N 591954329
        RUT PACIENTE :12345678-5  NOMBRE REGISTRAL:GLORIA ESTER SOTO PEREZ
        DIAGNOSTICO : LENTES OPTICOS LEJOS Y CERCA
        COSTO TOTAL $ 48.520   A PAGAR PERSONA BENEFICIARIA $ 24.260
        FECHA EMISION : 08/07/2025
    """
    text = block.text

    doc.familia = "bono_fonasa"
    doc.titulo = "Programa de atencion de salud FONASA"
    doc.tipo_documento.set(
        "Programa de atencion de salud FONASA", CONF_ALTA, "PROGRAMA DE ATENCION DE SALUD"
    )

    folio = re.search(
        r"programa\s*de\s*atenci[oó]n\s*de\s*salud\s*n[°ºo.]?\s*:?\s*(\d{5,12})",
        fold(text),
    )
    if folio:
        doc.folio.set(folio.group(1), CONF_ALTA, folio.group(0))

    # El RUT del paciente es el que sigue a "RUT PACIENTE"; el del establecimiento
    # y el del valorizador no sirven como identificacion del titular.
    rut = first_match(
        (
            r"rut\s*paciente\s*:?\s*([\d.]{6,12}-[\dkK])",
            r"rut\s*titular\s*:?\s*([\d.]{6,12}-[\dkK])",
            r"([\d.]{6,12}-[\dkK])\s*nombre\s*registral",
        ),
        text,
    )
    rut_normalizado = parse_rut(rut or "")
    if rut_normalizado and is_person_rut(rut_normalizado):
        doc.titular_rut.set(rut_normalizado, CONF_ALTA, rut or "")

    nombre = first_match((r"nombre\s*registral\s*:\s*([A-Za-zÁÉÍÓÚÑáéíóúñ ]{5,60})",), text)
    if nombre:
        doc.titular_nombre.set(clean_name(nombre).upper(), CONF_MEDIA, nombre)

    edad = first_match((r"edad\s*:?\s*(\d{1,3})",), text)
    if edad and int(edad) < 120:
        doc.titular_edad.set(int(edad), CONF_MEDIA, edad)

    sexo = first_match((r"sexo\s*:?\s*([FM])",), text)
    if sexo:
        doc.observaciones.set(
            f"Sexo registral: {sexo.upper()}", CONF_MEDIA, sexo
        )

    diagnostico = first_match((r"diagn[oó]stico\s*:\s*([A-ZÁÉÍÓÚÑ ]{4,80})",), text)
    if diagnostico:
        doc.diagnostico.set(clean_name(diagnostico).upper(), CONF_MEDIA, diagnostico)

    atencion = parse_date(first_match((r"desde\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",), text))
    if atencion:
        doc.fecha_atencion.set(atencion.isoformat(), CONF_MEDIA, atencion.strftime("%d-%m-%Y"))

    emision = parse_date(first_match((r"fecha\s*emisi[oó]n\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",), text))
    if emision:
        doc.fecha_emision.set(emision.isoformat(), CONF_ALTA, emision.strftime("%d-%m-%Y"))

    costo = first_match((r"costo\s*total\s*\$?\s*([\d.]{4,})",), text)
    if costo:
        doc.monto_bruto.set(parse_clp(costo), CONF_MEDIA, costo)

    copago = first_match(
        (r"a\s*pagar\s*persona\s*beneficiari[ao]\s*\$?\s*([\d.]{3,})",), text
    )
    if copago:
        doc.monto_copago.set(parse_clp(copago), CONF_MEDIA, copago)
        doc.monto_total.set(parse_clp(copago), CONF_MEDIA, copago, "Copago a pagar por la persona")

    aporte = first_match((r"aporte\s*fondo\s*nacional\s*de\s*salud\s*\$?\s*([\d.]{4,})",), text)
    if aporte:
        doc.monto_bonificacion.set(parse_clp(aporte), CONF_MEDIA, aporte)

    profesional = first_match((r"nombre\s*profesional\s*tratante\s*:\s*([A-ZÁÉÍÓÚÑ ]{5,60})",), text)
    if profesional:
        doc.profesional_nombre.set(clean_name(profesional).upper(), CONF_MEDIA, profesional)
    prof_rut = parse_rut(first_match((r"r\.?u\.?t\.?\s*profesional\s*([\d.]{7,12}-[\dkK])",), text) or "")
    if prof_rut:
        doc.profesional_rut.set(prof_rut, CONF_ALTA, prof_rut)

    establecimiento = first_match(
        (r"nombre\s*:\s*([A-ZÁÉÍÓÚÑ .]{5,50})", r"establecimiento\s*([A-ZÁÉÍÓÚÑ .]{5,50})"), text
    )
    if establecimiento:
        doc.emisor_nombre.set(clean_name(establecimiento).upper(), CONF_BAJA, establecimiento)

    _extract_prestaciones(block.lines, doc)
    return doc


