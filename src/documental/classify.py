"""Clasificacion de documentos por familia segun el texto del OCR.

Cada familia tiene un extractor propio. La clasificacion es por puntaje de
palabras clave, porque el OCR rara vez entrega el encabezado perfecto.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import CONF_ALTA, CONF_BAJA, CONF_MEDIA
from .normalizers import fold

FONASA = "bono_fonasa"
SII_BOLETA = "boleta_sii"
FARMACIA = "ticket_farmacia"
CLINICO = "documento_clinico"
PAGARE = "pagare"
OPTICA = "receta_optica"
LABORATORIO = "resultado_laboratorio"
DESCONOCIDO = "desconocido"

# Etiquetas legibles para el informe.
FAMILY_LABELS = {
    FONASA: "Bono de atencion FONASA",
    SII_BOLETA: "Boleta de honorarios electronica (SII)",
    FARMACIA: "Ticket de farmacia",
    CLINICO: "Documento clinico",
    PAGARE: "Pagare",
    OPTICA: "Receta optica",
    LABORATORIO: "Resultado de laboratorio",
    DESCONOCIDO: "Documento sin clasificar",
}

# (familia, palabras clave, peso). El puntaje final define la familia.
_KEYWORDS: tuple[tuple[str, tuple[str, ...], float], ...] = (
    (
        FONASA,
        (
            "bono de atencion", "bono de atencion ambulatoria", "fonasa",
            "bono electr", "prestacion", "bonificacion", "copago", "beneficiario",
            "nivel de atencion", "monto a pagar", "programa de atencion de salud",
            "aporte fondo nacional de salud", "beneficiaria",
        ),
        2.0,
    ),
    (
        SII_BOLETA,
        (
            "boleta de honorarios", "boleta electronica", "servicio de impuestos",
            "sii", "retencion", "honorarios", "giro", "neto", "iva",
        ),
        2.0,
    ),
    (
        FARMACIA,
        (
            "farmacia", "cruz verde", "ahumada", "salcobrand", "ticket",
            "medicamento", "bioequivalent", "receta medica", "doctor simi",
        ),
        2.5,
    ),
    (
        OPTICA,
        ("receta optica", "optica", "esf", "cil", "eje", "lejos", "cerca", "lentes"),
        3.0,
    ),
    (
        PAGARE,
        ("pagare", "debo y pagare", "vence", "interes", "fiador", "aviso de vencimiento"),
        3.0,
    ),
    (
        LABORATORIO,
        ("laboratorio", "resultado", "examen", "hemograma", "perfil bioquimico"),
        2.0,
    ),
    (
        CLINICO,
        (
            "informe medico", "certificado medico", "diagnostico", "atencion de urgencia",
            "hospital", "clinica", "consulta medica", "licencia medica", "epicrisis",
            "oftalmolog", "tecnologo medico", "medico tratante", "receta medica",
            "solicitud de examenes", "indicaciones", "control medico", "doctor",
        ),
        2.0,
    ),
)


@dataclass
class Classification:
    familia: str
    confianza: str
    puntajes: dict[str, float]

    @property
    def etiqueta(self) -> str:
        return FAMILY_LABELS.get(self.familia, self.familia)


def classify(text: str) -> Classification:
    """Determina la familia del documento a partir de su texto OCR."""
    folded = fold(text)
    scores: dict[str, float] = {}
    for familia, keywords, weight in _KEYWORDS:
        hits = sum(1 for keyword in keywords if keyword in folded)
        if hits:
            scores[familia] = scores.get(familia, 0.0) + hits * weight
    if not scores:
        return Classification(DESCONOCIDO, CONF_BAJA, {})
    best = max(scores, key=lambda key: scores[key])
    ordered = sorted(scores.values(), reverse=True)
    # Si la segunda opcion esta muy cerca, la clasificacion es dudosa.
    if len(ordered) > 1 and ordered[0] - ordered[1] < 2.0:
        confianza = CONF_MEDIA
    else:
        confianza = CONF_ALTA
    return Classification(best, confianza, scores)
