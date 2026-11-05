"""Extractor para boletas electronicas SII (servicios y comercio).

Cubre tanto la boleta de honorarios electronica como la boleta electronica
generica (optica, centro medico, etc.):

    EMISOR SPA
    R.U.T.: 77.777.777-7          BOLETA ELECTRONICA N 3605449
    GIRO ...
    Senor (es): TITULAR          R.U.T.: 12.345.678-5
    Fecha: 16/12/2025
    ...
    NETO / IVA / TOTAL
"""

from __future__ import annotations

import re

from ..layout import Block, Line
from ..models import CONF_ALTA, CONF_BAJA, CONF_MEDIA, Document, LineItem
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
    plausible_person_name,
    roman_letters_to_digits,
    rut_is_prestador,
    squeeze,
)

_TOTAL_LABELS = (
    r"total\s*(?:a\s*pagar)?\s*:?\s*\$",
    r"monto\s*total",
    r"total\s*:",
    r"total$",
)
_NETO_LABELS = (r"monto\s*neto", r"neto\s*:?", r"neto\s*\$")
_IVA_LABELS = (r"i\.?v\.?a\.?",)
_EXENTO_LABELS = (r"monto\s*exento", r"exento\s*:?")


def _amount_in_line(line: str) -> int | None:
    """Devuelve el ultimo monto con separador de miles de una linea."""
    matches = re.findall(r"\d{1,3}(?:[.\s]\d{3})+", line)
    if not matches:
        return None
    return parse_clp(matches[-1])


def _labelled_amount(
    lines: list[Line], labels: tuple[str, ...], *, search_next: int = 2
) -> tuple[int | None, str]:
    """Busca el monto asociado a una etiqueta (misma linea o siguientes)."""
    for index, line in enumerate(lines):
        folded = fold(line.text)
        for label in labels:
            if not re.search(label, folded):
                continue
            value = _amount_in_line(line.text)
            if value is not None:
                return value, line.text
            for offset in range(1, search_next + 1):
                if index + offset < len(lines):
                    value = _amount_in_line(lines[index + offset].text)
                    if value is not None:
                        return value, f"{line.text} {lines[index + offset].text}"
    return None, ""


def _rut_after(lines: list[Line], labels: tuple[str, ...]) -> tuple[str | None, str]:
    """Busca un RUT valido en las lineas que contienen alguna de las etiquetas."""
    for line in lines:
        folded = fold(line.text)
        if any(re.search(label, folded) for label in labels):
            rut = parse_rut(line.text)
            if rut:
                return rut, line.text
    return None, ""


def _name_after_titular_label(lines: list[Line]) -> tuple[str, str]:
    """Extrae el nombre del cliente desde 'Senor (es):' o 'Sr(a).:'."""
    for line in lines:
        folded = fold(line.text)
        if not re.search(r"(?:senor(?:es)?|sr\s*\(?a?\)?|cliente)\s*:?", folded):
            continue
        remainder = line.text.split(":", 1)[1] if ":" in line.text else line.text
        remainder = re.split(r"r\.?\s*u\.?\s*t\.?", remainder, flags=re.IGNORECASE)[0]
        candidate = clean_name(remainder)
        if looks_like_person_name(candidate):
            return candidate, line.text
    return "", ""


def _collect_ruts(lines: list[Line]) -> list[str]:
    """Todos los RUT validos distintos, en orden de aparicion."""
    ruts: list[str] = []
    for line in lines:
        for chunk in re.findall(r"\d[\d.\s]{4,12}-\s*[0-9kK]", line.text):
            rut = parse_rut(chunk)
            if rut and rut not in ruts:
                ruts.append(rut)
    return ruts


def _total_label_amount(lines: list[Line]) -> tuple[int | None, str]:
    """Monto de la linea que contiene la etiqueta TOTAL (solo esa linea).

    En boletas SII el total aparece como "TOTAL 3.900" y a veces la linea de
    items contiene numeros mayores, por lo que buscar "el mayor monto" daria un
    resultado incorrecto. Se toma la cifra inmediatamente posterior a la
    etiqueta; si no hay ninguna, se usa la ultima cifra de esa misma linea.
    """
    for line in lines:
        folded = fold(line.text)
        if not re.search(r"\btotal\b", folded):
            continue
        texto = line.text
        match = re.search(r"(?i)\btotal\b[^\d$]{0,20}\$?\s*(\d{1,3}(?:[.\s]\d{3})+|\d{3,9})", texto)
        if match:
            valor = parse_clp(match.group(1))
            if valor is not None:
                return valor, line.text
        valor = _amount_in_line(texto)
        if valor is not None:
            return valor, line.text
    return None, ""


def extract_sii(block: Block, doc: Document) -> Document:
    """Completa los campos de una boleta electronica del SII."""
    lines = block.lines
    text = block.text

    doc.familia = "boleta_sii"
    doc.tipo_documento.set("Boleta electronica SII", CONF_MEDIA, "BOLETA ELECTRONICA")

    folio = first_match(
        (
            r"boleta\s*(?:electr[oó]nica|de\s*honorarios)?[^\d\n]{0,25}(\d{5,12})",
            r"n\s*[°ºo.]*\s*(\d{5,12})",
        ),
        text,
    )
    if folio:
        doc.folio.set(folio, CONF_ALTA, folio)

    # Emisor: primera linea con razon social.
    for line in lines[:5]:
        head = re.split(r"r\.?\s*u\.?\s*t", line.text, flags=re.IGNORECASE)[0]
        candidate = clean_name(head)
        if not candidate or any(ch.isdigit() for ch in candidate):
            continue
        if re.search(r"(SPA|LTDA|S\.?A\.?|E\.?I\.?R\.?L|LIMITADA)", candidate, re.IGNORECASE):
            doc.emisor_nombre.set(candidate.upper(), CONF_MEDIA, line.text)
            break
    if doc.emisor_nombre.is_empty and len(lines) > 1:
        candidate = clean_name(lines[0].text)
        if looks_like_person_name(candidate):
            doc.emisor_nombre.set(candidate.upper(), CONF_BAJA, lines[0].text)

    emisor_rut, raw_emisor = _rut_after(lines[:8], (r"r\.?\s*u\.?\s*t", r"rut"))
    if emisor_rut:
        doc.emisor_rut.set(emisor_rut, CONF_ALTA, raw_emisor)

    giro = first_match((r"giro\s*:?\s*([A-Za-zÁÉÍÓÚÑ ]{3,40})",), text)
    if giro:
        doc.emisor_giro.set(clean_name(giro).upper(), CONF_MEDIA, giro)

    # Titular / cliente: solo se acepta nombre con etiqueta explicita o el que
    # acompaña a un RUT de persona natural. Nunca se usa la razon social.
    nombre, raw_nombre = _name_after_titular_label(lines)
    if plausible_person_name(nombre):
        doc.titular_nombre.set(nombre.upper(), CONF_MEDIA, raw_nombre)

    ruts = _collect_ruts(lines)
    person_ruts = [r for r in ruts if is_person_rut(r) and not rut_is_prestador(text, r)]
    titular_rut = next((r for r in person_ruts if r != doc.emisor_rut.value), None)
    if titular_rut is None and person_ruts:
        titular_rut = person_ruts[0]
    if titular_rut:
        doc.titular_rut.set(titular_rut, CONF_MEDIA, titular_rut)

    if doc.titular_nombre.is_empty and titular_rut:
        # Se busca el nombre en la misma linea del RUT del titular.
        for line in lines:
            if titular_rut in (parse_rut(line.text) or ""):
                head = re.split(r"(?i)r\.?\s*u\.?\s*t", line.text)[0]
                head = re.sub(r"(?i)^\s*(senor(es)?|sr\s*\(?a?\)?|cliente)\s*:?", "", head)
                candidate = clean_name(head)
                if plausible_person_name(candidate):
                    doc.titular_nombre.set(candidate.upper(), CONF_BAJA, line.text)
                break

    # Si el nombre no se pudo leer pero hay RUT de titular, se completa luego
    # desde la configuracion del caso (titulares.py).

    # Fechas (el OCR a veces convierte digitos en letras romanas: "4-0I-20026").
    fecha_campo = None
    for line in lines:
        if re.search(r"fecha", fold(line.text)):
            fecha_campo = parse_date(roman_letters_to_digits(line.text))
            if fecha_campo:
                doc.fecha_emision.set(fecha_campo.isoformat(), CONF_MEDIA, line.text)
                break
    if fecha_campo is None:
        fecha_campo = parse_date(roman_letters_to_digits(text))
        if fecha_campo:
            doc.fecha_emision.set(
                fecha_campo.isoformat(), CONF_BAJA, "Fecha detectada sin etiqueta"
            )

    # Montos. El total es la cifra que acompaña la etiqueta TOTAL en la misma
    # linea (no la ultima cifra de la linea, que puede ser un numero de item).
    total, raw_total = _total_label_amount(lines)
    if total is not None:
        doc.monto_total.set(total, CONF_MEDIA, raw_total)
    neto, raw_neto = _labelled_amount(lines, _NETO_LABELS)
    if neto is not None:
        doc.monto_neto.set(neto, CONF_MEDIA, raw_neto)
    iva, raw_iva = _labelled_amount(lines, _IVA_LABELS)
    if iva is not None:
        doc.monto_iva.set(iva, CONF_BAJA, raw_iva)
    exento, raw_exento = _labelled_amount(lines, _EXENTO_LABELS)
    if exento is not None:
        doc.observaciones.set(
            f"Documento exento por {format_clp(exento)}", CONF_MEDIA, raw_exento
        )
        if doc.monto_total.is_empty:
            doc.monto_total.set(exento, CONF_MEDIA, raw_exento, "Total exento")

    _extract_items(lines, doc)
    return doc


def _extract_items(lines: list[Line], doc: Document) -> None:
    """Extrae las lineas de detalle (descripcion + precios)."""
    in_items = False
    for line in lines:
        folded = fold(line.text)
        if re.search(r"(descripcion|detalle)\s*(?:cantidad|precio|cuotas)", folded):
            in_items = True
            continue
        if re.search(r"(sub\s*total|descuento|^neto|^i\.?v\.?a|total|timbre)", folded):
            in_items = False
            continue
        if not in_items:
            continue
        text = squeeze(line.text)
        if not re.search(r"[A-Za-zÁÉÍÓÚÑ]{4,}", text):
            continue
        amounts = re.findall(r"\d{1,3}(?:[.\s]\d{3})+|\b\d{1,3}\b", text)
        descripcion = re.split(r"\s{2,}", text)[0]
        item = LineItem(
            descripcion=clean_name(re.sub(r"^\d+\s*[-.]?\s*", "", descripcion)),
            raw=text,
            confidence=CONF_MEDIA if line.score >= 0.8 else CONF_BAJA,
        )
        numeric = [n for n in (parse_clp(a) for a in amounts) if n]
        if numeric:
            item.total = numeric[-1]
        if len(numeric) >= 2:
            item.valor_unitario = numeric[-2]
        if len(numeric) >= 3:
            item.cantidad = str(numeric[-3])
        if item.descripcion:
            doc.items.append(item)

