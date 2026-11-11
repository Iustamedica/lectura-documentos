"""Naturaleza de la fuente documental.

La *familia* dice como se usa un documento dentro del expediente (escrito,
resolucion, contrato...). La *naturaleza* dice **que es la fuente**:

* ``expediente``: pieza de un expediente judicial (demanda, contestacion,
  prueba, sentencia, apelacion);
* ``jurisprudencia``: fallo publicado de un tribunal (Corte Suprema, Corte de
  Apelaciones, Tribunal Constitucional);
* ``resolucion``: acto administrativo de una autoridad (resolucion exenta,
  dictamen, sancion, sumario);
* ``doctrina``: libro, capitulo, articulo de revista, paper o publicacion;
* ``documento``: boleta, factura, carta, contrato u otro documento de trabajo.

El clasificador usa el texto OCR completo y palabras con peso negativo para
resolver los cruces tipicos: una sentencia citada dentro de una demanda no
convierte la demanda en jurisprudencia, y una resolucion que menciona
"contrato" no es un contrato.
"""

from __future__ import annotations

import re

from ...classify import Classification
from ...models import CONF_ALTA, CONF_BAJA, CONF_MEDIA
from ...normalizers import fold

EXPEDIENTE = "expediente"
JURISPRUDENCIA = "jurisprudencia"
RESOLUCION = "resolucion"
DOCTRINA = "doctrina"
DOCUMENTO = "documento"

NATURALEZAS: tuple[str, ...] = (
    EXPEDIENTE,
    JURISPRUDENCIA,
    RESOLUCION,
    DOCTRINA,
    DOCUMENTO,
)

ETIQUETAS: dict[str, str] = {
    EXPEDIENTE: "Expediente judicial",
    JURISPRUDENCIA: "Jurisprudencia",
    RESOLUCION: "Resolucion administrativa",
    DOCTRINA: "Doctrina",
    DOCUMENTO: "Documento",
}

# Orden de desempate: ante un puntaje igual gana la fuente mas especifica.
_ORDEN = {clave: posicion for posicion, clave in enumerate(NATURALEZAS)}

_RE_ROL = re.compile(
    r"\b(?:rol|rit)\s*(?:n[.\u00ba\u00b0]?\s*)?[a-z]{0,3}[- ]?\d{1,6}[- ]?\d{2,4}\b"
)

# (naturaleza, palabras clave, peso)
_KEYWORDS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    (
        EXPEDIENTE,
        (
            "en lo principal",
            "otrosi",
            "por recibidos",
            "recibase la causa a prueba",
            "recibese la causa a prueba",
            "cuaderno",
            "caratula",
            "fojas",
            "demandante",
            "demandado",
            "proveido",
            "secretario",
            "receptor",
            "cedula de notificacion",
            "notificacion electronica",
            "expediente",
            "tribunal",
            "juzgado",
            "demanda",
            "contestacion",
            "replica",
            "duplica",
            "recurso de apelacion",
            "recurso de casacion",
            "recurso de queja",
            "querella",
            "formalizacion",
        ),
        2.0,
    ),
    (
        JURISPRUDENCIA,
        (
            "corte suprema",
            "tribunal constitucional",
            "corte de apelaciones",
            "jurisprudencia",
            "gaceta juridica",
            "revista de derecho",
            "sentencia de reemplazo",
            "voto de minoria",
            "disidencia",
            "abogado integrante",
            "redactor",
            "ministro",
            "considerando",
            "fallo",
            "se confirma la sentencia",
            "se revoca la sentencia",
            "casacion en el fondo",
            "casacion en la forma",
        ),
        1.8,
    ),
    (
        RESOLUCION,
        (
            "resolucion exenta",
            "resolucion afecta",
            "acto administrativo",
            "procedimiento administrativo",
            "sumario administrativo",
            "investigacion sumaria",
            "dictamen",
            "contraloria",
            "superintendencia",
            "intendencia",
            "municipalidad",
            "gobierno regional",
            "seremi",
            "subsecretaria",
            "ministerio",
            "servicio publico",
            "resuelvo",
            "sancion",
            "multa",
            "ordinario",
            "decreto",
            "notifiquese",
            "vistos",
        ),
        1.8,
    ),
    (
        DOCTRINA,
        (
            "isbn",
            "issn",
            "doi",
            "abstract",
            "resumen",
            "summary",
            "palabras clave",
            "capitulo",
            "libro",
            "compendio",
            "editorial",
            "revista",
            "publicacion",
            "universidad",
            "facultad",
            "facultad de derecho",
            "tesis",
            "tesis para optar",
            "memoria para optar",
            "paper",
            "articulo",
            "vol.",
            "num.",
            "pp.",
            "edicion",
            "primera edicion",
            "derechos reservados",
            "traduccion",
            "obra",
            "autor",
            "catedra",
            "ensayo",
            "monografia",
            "comentario de jurisprudencia",
            "recibido",
            "aceptado",
            "correspondencia",
            "referencias",
            "bibliografia",
        ),
        1.8,
    ),
    (
        DOCUMENTO,
        (
            "boleta",
            "factura",
            "comprobante",
            "contrato",
            "carta",
            "estimado",
            "senor",
            "giro",
            "iva",
            "total a pagar",
            "poder",
            "certificado",
            "pagare",
            "cheque",
            "cotizacion",
            "orden de compra",
            "recibo",
            "memorandum",
            "solicitud",
            "declaracion jurada",
        ),
        1.5,
    ),
)

# Se citan dentro de otra fuente y no deben contarla.
_NEGATIVOS: dict[str, tuple[str, ...]] = {
    EXPEDIENTE: (
        "isbn",
        "issn",
        "doi",
        "abstract",
        "resumen",
        "palabras clave",
        "gaceta juridica",
        "revista de derecho",
        "resolucion exenta",
        "dictamen",
        "contraloria",
        "sumario administrativo",
        "tesis para optar",
        "memoria para optar",
        "primera edicion",
        "universidad",
        "facultad",
    ),
    JURISPRUDENCIA: (
        "en lo principal",
        "por recibidos",
        "cuaderno",
        "fojas",
        "resolucion exenta",
        "isbn",
        "issn",
        "doi",
        "abstract",
        "resumen",
        "palabras clave",
        "tesis para optar",
        "primera edicion",
        "universidad",
        "facultad",
    ),
    RESOLUCION: (
        "en lo principal",
        "por recibidos",
        "corte suprema",
        "isbn",
        "abstract",
    ),
    DOCTRINA: (
        "en lo principal",
        "por recibidos",
        "resolucion exenta",
        "boleta electronica",
        "factura electronica",
    ),
    DOCUMENTO: (
        "en lo principal",
        "considerando",
        "resuelvo",
        "corte suprema",
        "isbn",
        "issn",
        "doi",
        "primera edicion",
        "tesis para optar",
        "derechos reservados",
    ),
}

# Marcadores editoriales que casi solo aparecen en doctrina: si estan, la
# balanza se inclina fuerte hacia alla aunque el texto cite fallos.
_FUERTES_DOCTRINA: tuple[str, ...] = (
    "issn",
    "doi",
    "abstract",
    "palabras clave",
    "tesis para optar",
    "memoria para optar",
    "primera edicion",
    "derechos reservados",
    "compendio",
    "referencias bibliograficas",
)


def _cuenta(folded: str, keywords: tuple[str, ...]) -> int:
    """Cuenta palabras clave; los tokens cortos se buscan como palabra completa."""
    total = 0
    for keyword in keywords:
        if len(keyword) <= 4 and keyword.isalpha():
            if re.search(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", folded):
                total += 1
        elif keyword in folded:
            total += 1
    return total


def clasificar(texto: str) -> Classification:
    """Devuelve la naturaleza de la fuente y su confianza."""
    folded = fold(texto or "")
    scores: dict[str, float] = {}

    for naturaleza, keywords, peso in _KEYWORDS:
        encontrados = _cuenta(folded, keywords)
        if encontrados:
            scores[naturaleza] = scores.get(naturaleza, 0.0) + encontrados * peso

    for naturaleza, keywords in _NEGATIVOS.items():
        if naturaleza in scores:
            scores[naturaleza] = max(
                0.0, scores[naturaleza] - 1.5 * _cuenta(folded, keywords)
            )

    fuertes = _cuenta(folded, _FUERTES_DOCTRINA)
    if fuertes:
        scores[DOCTRINA] = scores.get(DOCTRINA, 0.0) + 4.0 * min(fuertes, 3)

    if _RE_ROL.search(folded):
        scores[EXPEDIENTE] = scores.get(EXPEDIENTE, 0.0) + 8.0
    if "corte suprema" in folded or "tribunal constitucional" in folded:
        scores[JURISPRUDENCIA] = scores.get(JURISPRUDENCIA, 0.0) + 4.0
    if "isbn" in folded or "doi" in folded:
        scores[DOCTRINA] = scores.get(DOCTRINA, 0.0) + 5.0

    # Un documento corriente siempre es una opcion valida (nunca queda vacio).
    scores[DOCUMENTO] = scores.get(DOCUMENTO, 0.0) + 1.0

    mejor = max(scores, key=lambda clave: (scores[clave], -_ORDEN[clave]))
    ordenados = sorted(scores.values(), reverse=True)
    segundo = ordenados[1] if len(ordenados) > 1 else 0.0
    if scores[mejor] >= 6.0 and scores[mejor] - segundo >= 3.0:
        confianza = CONF_ALTA
    elif scores[mejor] >= 3.0:
        confianza = CONF_MEDIA
    else:
        confianza = CONF_BAJA
    return Classification(mejor, confianza, scores)


def etiqueta(naturaleza: str) -> str:
    """Nombre legible de una naturaleza (para el revisor y el informe)."""
    return ETIQUETAS.get(naturaleza, naturaleza)
