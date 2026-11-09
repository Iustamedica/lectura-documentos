"""Clasificacion de documentos legales por familia.

Mismo mecanismo que el perfil de salud (puntaje por palabras clave), con dos
cuidados propios del texto judicial:

* un escrito **cita** "sentencia" o "resuelvo" sin ser una resolucion;
* una resolucion **menciona** "demanda" o "contrato" sin ser un escrito ni un
  contrato.

Por eso hay palabras con peso negativo que restan a la familia equivocada.
"""

from __future__ import annotations

import re

from ...classify import Classification
from ...models import CONF_ALTA, CONF_BAJA, CONF_MEDIA
from ...normalizers import fold

ESCRITO = "escrito"
RESOLUCION = "resolucion"
NOTIFICACION = "notificacion"
CONTRATO = "contrato"
COMPROBANTE = "comprobante"
PODER_CERTIFICADO = "poder_certificado"
INFORME = "informe"
OTRO = "otro"

FAMILY_LABELS = {
    ESCRITO: "Escrito de parte",
    RESOLUCION: "Resolucion del tribunal",
    NOTIFICACION: "Notificacion",
    CONTRATO: "Contrato",
    COMPROBANTE: "Comprobante de pago",
    PODER_CERTIFICADO: "Poder o certificado",
    INFORME: "Informe o peritaje",
    OTRO: "Documento sin clasificar",
}

# (familia, palabras clave, peso)
_KEYWORDS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    (
        NOTIFICACION,
        (
            "cedula de notificacion",
            "notificacion electronica",
            "certifico que notifique",
            "notifiquese",
            "notificado",
            "notificacion",
            "casilla judicial",
        ),
        3.0,
    ),
    (
        RESOLUCION,
        (
            "sentencia definitiva",
            "sentencia interlocutoria",
            "auto de prueba",
            "recibese la causa a prueba",
            "recibase la causa a prueba",
            "por recibidos",
            "agreguese",
            "tengase presente",
            "proveyo",
            "proveido",
            "vistos",
            "considerando",
            "resuelvo",
            "por tanto",
            "secretario",
            "ministro",
            "formalizacion",
            "sobreseimiento",
            "prision preventiva",
            "medida cautelar",
            "medida de proteccion",
            "condeno",
            "absuelvo",
        ),
        2.0,
    ),
    (
        ESCRITO,
        (
            "en lo principal",
            "solicito",
            "ruego",
            "acompano",
            "tengase por",
            "por interpuesta",
            "demanda",
            "contestando la demanda",
            "contesto",
            "replica",
            "duplica",
            "recurso de apelacion",
            "recurso de casacion",
            "recurso de reposicion",
            "recurso de queja",
            "apelo",
            "opongo excepciones",
            "ofrezco prueba",
            "alegato",
            "desisto",
            "me allano",
            "querella",
            "denuncia",
            "acusacion fiscal",
            "demanda de divorcio",
            "demanda de alimentos",
            "cuidado personal",
        ),
        2.0,
    ),
    (
        CONTRATO,
        (
            "contrato de arriendo",
            "contrato de trabajo",
            "contrato de compraventa",
            "contrato de prestacion de servicios",
            "contrato de mutuo",
            "contrato",
            "comparecen",
            "clausula",
            "arrendador",
            "arrendatario",
            "empleador",
            "trabajador",
            "prestamista",
            "deudor",
        ),
        2.0,
    ),
    (
        COMPROBANTE,
        (
            "boleta electronica",
            "factura electronica",
            "boleta de honorarios",
            "boleta exenta",
            "comprobante de pago",
            "comprobante de transferencia",
            "comprobante de deposito",
            "servicio de impuestos internos",
            "giro",
            "neto",
            "iva",
            "total a pagar",
        ),
        2.0,
    ),
    (
        PODER_CERTIFICADO,
        (
            "poder notarial",
            "poder especial",
            "poder simple",
            "mandato judicial",
            "notaria",
            "repertorio",
            "certificado de nacimiento",
            "certificado de matrimonio",
            "certificado de antecedentes",
            "certificado de vigencia",
            "personeria",
            "representante legal",
            "cedula de identidad",
            "pasaporte",
        ),
        2.0,
    ),
    (
        INFORME,
        (
            "informe pericial",
            "perito",
            "pericia",
            "tasacion",
            "avaluo",
            "valuacion",
            "informe tecnico",
            "informe social",
        ),
        2.5,
    ),
)

# Palabras que restan puntaje a una familia (se citan sin pertenecer a ella).
_NEGATIVOS: dict[str, tuple[str, ...]] = {
    RESOLUCION: ("en lo principal", "solicito", "ruego a us.", "por tanto ruego"),
    ESCRITO: ("vistos", "considerando", "resuelvo", "proveyo", "sentencia definitiva"),
    CONTRATO: ("boleta electronica", "factura electronica"),
}


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
    """Determina la familia del documento a partir de su texto."""
    folded = fold(texto)
    scores: dict[str, float] = {}
    for familia, keywords, weight in _KEYWORDS:
        hits = _cuenta(folded, keywords)
        if hits:
            scores[familia] = scores.get(familia, 0.0) + hits * weight
    for familia, keywords in _NEGATIVOS.items():
        if familia in scores:
            scores[familia] = max(0.0, scores[familia] - 2.0 * _cuenta(folded, keywords))
    scores = {familia: valor for familia, valor in scores.items() if valor > 0}
    if not scores:
        return Classification(OTRO, CONF_BAJA, {})
    mejor = max(scores, key=lambda clave: scores[clave])
    ordenados = sorted(scores.values(), reverse=True)
    confianza = CONF_ALTA
    if len(ordenados) > 1 and ordenados[0] - ordenados[1] < 2.0:
        confianza = CONF_MEDIA
    return Classification(mejor, confianza, scores)
