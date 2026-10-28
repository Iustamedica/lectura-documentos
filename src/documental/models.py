"""Modelo de datos del expediente documental.

El objetivo es que cada dato extraido sea auditable: se guarda el valor
normalizado, el texto original del OCR y un nivel de confianza. El Word final y
el revisor HTML se generan a partir de esta estructura, de modo que corregir un
dato en el revisor y regenerar el Word es un flujo directo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Niveles de confianza usados en todo el sistema.
CONF_ALTA = "alta"       # dato validado (ej. RUT con DV correcto) u OCR claro
CONF_MEDIA = "media"     # patron reconocido pero con ruido de OCR
CONF_BAJA = "baja"       # heuristica; requiere revision humana
CONF_FALTA = "faltante"  # no se encontro

CONFIDENCE_ORDER = {CONF_ALTA: 0, CONF_MEDIA: 1, CONF_BAJA: 2, CONF_FALTA: 3}


@dataclass
class Field:
    """Un dato extraido con su trazabilidad."""

    value: Any = None
    confidence: str = CONF_FALTA
    raw: str = ""            # fragmento de OCR del que se obtuvo
    note: str = ""           # observacion para el revisor
    edited: bool = False     # True si un humano lo corrigio en el revisor

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "Field":
        if not data:
            return Field()
        return Field(
            value=data.get("value"),
            confidence=data.get("confidence", CONF_FALTA),
            raw=data.get("raw", ""),
            note=data.get("note", ""),
            edited=bool(data.get("edited", False)),
        )

    @property
    def is_empty(self) -> bool:
        return self.value in (None, "", [], {})

    def set(
        self, value: Any, confidence: str = CONF_MEDIA, raw: str = "", note: str = ""
    ) -> "Field":
        """Asigna valor solo si el nuevo dato es mejor que el actual.

        Evita que un patron de baja confianza pise un valor ya validado.
        """
        if value in (None, "", [], {}):
            return self
        current_rank = CONFIDENCE_ORDER.get(self.confidence, 9)
        new_rank = CONFIDENCE_ORDER.get(confidence, 9)
        if self.is_empty or new_rank < current_rank:
            self.value = value
            self.confidence = confidence
            self.raw = raw or self.raw
            self.note = note
        return self

    def mark_missing(self, note: str, confidence: str = CONF_BAJA) -> "Field":
        """Registra un campo vacio con el motivo (para el anexo de verificacion).

        Se usa cuando el dato existe en el documento pero no es atribuible al
        titular (por ejemplo, el RUT impreso es el del centro medico).
        """
        if self.is_empty:
            self.value = None
            self.confidence = confidence
            self.note = note
        return self


@dataclass
class LineItem:
    """Una prestacion, servicio o producto dentro de un documento."""

    codigo: str = ""
    descripcion: str = ""
    cantidad: str = ""
    valor_unitario: int | None = None
    bonificacion: int | None = None
    copago: int | None = None
    total: int | None = None
    raw: str = ""
    confidence: str = CONF_MEDIA

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LineItem":
        allowed = set(LineItem.__dataclass_fields__)
        return LineItem(**{k: v for k, v in data.items() if k in allowed})


# Campos escalares de un documento, en el orden en que se muestran en el informe.
DOCUMENT_FIELD_NAMES = (
    "tipo_documento", "folio",
    "emisor_nombre", "emisor_rut", "emisor_giro", "emisor_direccion",
    "titular_nombre", "titular_rut", "titular_edad", "titular_direccion",
    "titular_contacto", "titular_prevision",
    "profesional_nombre", "profesional_rut", "profesional_especialidad",
    "fecha_emision", "fecha_atencion", "fecha_vencimiento", "hora",
    "monto_bruto", "monto_bonificacion", "monto_copago", "monto_neto",
    "monto_iva", "monto_total", "medio_pago",
    "diagnostico", "observaciones",
)

# Campos cuyo vacio o baja confianza hacen que el documento no sea confiable.
CRITICAL_FIELD_NAMES = (
    "tipo_documento", "folio", "titular_nombre", "titular_rut",
    "fecha_emision", "monto_total",
)


@dataclass
class Document:
    """Un documento independiente (una boleta, un bono, una receta, etc.)."""

    doc_id: str
    source_file: str
    page: int
    index_in_page: int
    familia: str = "desconocido"
    familia_confianza: str = CONF_BAJA
    titulo: str = ""

    tipo_documento: Field = field(default_factory=Field)
    folio: Field = field(default_factory=Field)
    emisor_nombre: Field = field(default_factory=Field)
    emisor_rut: Field = field(default_factory=Field)
    emisor_giro: Field = field(default_factory=Field)
    emisor_direccion: Field = field(default_factory=Field)

    titular_nombre: Field = field(default_factory=Field)
    titular_rut: Field = field(default_factory=Field)
    titular_edad: Field = field(default_factory=Field)
    titular_direccion: Field = field(default_factory=Field)
    titular_contacto: Field = field(default_factory=Field)
    titular_prevision: Field = field(default_factory=Field)

    profesional_nombre: Field = field(default_factory=Field)
    profesional_rut: Field = field(default_factory=Field)
    profesional_especialidad: Field = field(default_factory=Field)

    fecha_emision: Field = field(default_factory=Field)
    fecha_atencion: Field = field(default_factory=Field)
    fecha_vencimiento: Field = field(default_factory=Field)
    hora: Field = field(default_factory=Field)

    monto_bruto: Field = field(default_factory=Field)
    monto_bonificacion: Field = field(default_factory=Field)
    monto_copago: Field = field(default_factory=Field)
    monto_neto: Field = field(default_factory=Field)
    monto_iva: Field = field(default_factory=Field)
    monto_total: Field = field(default_factory=Field)
    medio_pago: Field = field(default_factory=Field)

    diagnostico: Field = field(default_factory=Field)
    observaciones: Field = field(default_factory=Field)

    items: list[LineItem] = field(default_factory=list)
    texto_ocr: str = ""
    imagen: str = ""  # ruta relativa al recorte del documento

    def fields(self) -> dict[str, Field]:
        """Campos escalares (Field) del documento, indexados por nombre."""
        return {name: getattr(self, name) for name in DOCUMENT_FIELD_NAMES}

    def field(self, name: str) -> Field:
        return getattr(self, name)

    def confianza_global(self) -> str:
        """Peor confianza entre los campos criticos del documento."""
        worst = CONF_ALTA
        for name in CRITICAL_FIELD_NAMES:
            actual = self.field(name).confidence
            if CONFIDENCE_ORDER.get(actual, 9) > CONFIDENCE_ORDER[worst]:
                worst = actual
        return worst

    def campos_a_revisar(self) -> list[str]:
        """Campos criticos vacios o de baja confianza (alimenta el semaforo)."""
        return [
            name
            for name in CRITICAL_FIELD_NAMES
            if CONFIDENCE_ORDER.get(self.field(name).confidence, 9)
            >= CONFIDENCE_ORDER[CONF_BAJA]
        ]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "doc_id": self.doc_id,
            "source_file": self.source_file,
            "page": self.page,
            "index_in_page": self.index_in_page,
            "familia": self.familia,
            "familia_confianza": self.familia_confianza,
            "titulo": self.titulo,
            "texto_ocr": self.texto_ocr,
            "imagen": self.imagen,
            "items": [item.to_dict() for item in self.items],
        }
        for name, value in self.fields().items():
            data[name] = value.to_dict()
        return data

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Document":
        doc = Document(
            doc_id=data["doc_id"],
            source_file=data["source_file"],
            page=data.get("page", 1),
            index_in_page=data.get("index_in_page", 1),
            familia=data.get("familia", "desconocido"),
            familia_confianza=data.get("familia_confianza", CONF_BAJA),
            titulo=data.get("titulo", ""),
            texto_ocr=data.get("texto_ocr", ""),
            imagen=data.get("imagen", ""),
        )
        for name in DOCUMENT_FIELD_NAMES:
            setattr(doc, name, Field.from_dict(data.get(name)))
        doc.items = [LineItem.from_dict(i) for i in data.get("items", [])]
        return doc


@dataclass
class Titular:
    """Persona titular de uno o mas documentos del expediente."""

    rut: str
    nombre: str
    relacion: str = ""  # "titular", "hijo de ...", etc.
    notas: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Expediente:
    """Conjunto de documentos procesados de una carpeta."""

    carpeta: str
    generado: str
    documentos: list[Document] = field(default_factory=list)
    titulares: list[Titular] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "carpeta": self.carpeta,
            "generado": self.generado,
            "titulares": [t.to_dict() for t in self.titulares],
            "advertencias": self.advertencias,
            "documentos": [d.to_dict() for d in self.documentos],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Expediente":
        return Expediente(
            carpeta=data.get("carpeta", ""),
            generado=data.get("generado", ""),
            titulares=[Titular(**t) for t in data.get("titulares", [])],
            advertencias=data.get("advertencias", []),
            documentos=[Document.from_dict(d) for d in data.get("documentos", [])],
        )

