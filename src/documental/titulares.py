"""Agrupacion de documentos por titular.

Un mismo expediente puede contener documentos de varias personas (en este caso
la madre y el hijo). El agrupamiento se hace por RUT cuando esta disponible y
por nombre normalizado cuando no, y se resuelve el parentesco declarado en la
configuracion del caso.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .models import CONF_FALTA, Document, Expediente, Titular
from .normalizers import fold, parse_rut, rut_body


@dataclass
class TitularConfig:
    """Definicion manual de un titular conocida de antemano."""

    rut: str
    nombre: str
    relacion: str = ""
    notas: str = ""
    alias: list[str] = field(default_factory=list)

    def matches(self, rut: str | None, nombre: str | None) -> bool:
        """True si el RUT o algun alias coincide con este titular."""
        if rut and self.rut and rut_body(rut) == rut_body(self.rut):
            return True
        if nombre:
            for candidate in [self.nombre, *self.alias]:
                if candidate and _name_key(candidate) == _name_key(nombre):
                    return True
                if candidate and name_contains(candidate, nombre):
                    return True
        return False


def _name_key(name: str) -> str:
    """Clave de comparacion: palabras ordenadas alfabeticamente y sin tildes."""
    words = sorted(re.findall(r"[a-zñ]+", fold(name)))
    return " ".join(words)


def name_contains(candidate: str, observed: str) -> bool:
    """True si el nombre observado esta contenido en el candidato.

    Tolerado a proposito:
      - que falten palabras: el OCR omite el segundo apellido o el nombre de pila
        ("GLORIA ESTER SOTO" dentro de "GLORIA ESTER SOTO PEREZ");
      - que una palabra quede truncada al final ("GLORIA ESTER SOT"): el OCR corta
        la ultima palabra del renglon, por lo que "SOT" debe aceptarse como
        prefijo de "SOTO".

    Se exige un minimo de 3 caracteres por palabra para no unir titulares
    distintos por particulas sueltas ("DE", "MA").
    """
    words = re.findall(r"[a-zñ]{3,}", fold(observed))
    if len(words) < 2:
        return False
    haystack = re.findall(r"[a-zñ]{3,}", fold(candidate))
    for word in words:
        if not any(h == word or (len(word) >= 3 and h.startswith(word)) for h in haystack):
            return False
    return True


def load_titulares(path: Path) -> list[TitularConfig]:
    """Carga la definicion de titulares desde un JSON de caso.

    Formato:
        {
          "titulares": [
            {"rut": "12.345.678-5", "nombre": "GLORIA ESTER SOTO PEREZ",
             "relacion": "madre", "alias": ["GLORIA ESTER SOTO"]}
          ]
        }
    """
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("titulares", raw) if isinstance(raw, dict) else raw
    result: list[TitularConfig] = []
    for entry in entries:
        rut = parse_rut(entry.get("rut", "")) or entry.get("rut", "")
        result.append(
            TitularConfig(
                rut=rut,
                nombre=(entry.get("nombre") or "").upper(),
                relacion=entry.get("relacion", ""),
                notas=entry.get("notas", ""),
                alias=[str(a).upper() for a in entry.get("alias", [])],
            )
        )
    return result


# Cuantos documentos debe respaldar un titular que no esta declarado en la ficha
# del caso. Un RUT o un nombre visto una sola vez suele ser un profesional, un
# acompanante o basura de OCR: en un informe para juicio no puede convertirse en
# titular sin respaldo.
MIN_DOCUMENTOS_POR_TITULAR = 2


@dataclass
class AnalisisTitulares:
    """Resultado de agrupar documentos por titular.

    ``descartados`` trae los grupos que no alcanzaron el minimo de respaldo y que
    por lo tanto NO se informan como titulares. Se reportan como advertencia para
    que el abogado los revise y, si corresponde, los declare en ``caso.json``.
    """

    titulares: list[Titular]
    descartados: list[tuple[Titular, int]] = field(default_factory=list)


def build_titulares(
    documentos: list[Document],
    config: list[TitularConfig] | None = None,
    min_documentos: int = MIN_DOCUMENTOS_POR_TITULAR,
) -> list[Titular]:
    """Devuelve solo la lista de titulares (ver ``analizar_titulares``)."""
    return analizar_titulares(documentos, config, min_documentos).titulares


def analizar_titulares(
    documentos: list[Document],
    config: list[TitularConfig] | None = None,
    min_documentos: int = MIN_DOCUMENTOS_POR_TITULAR,
) -> AnalisisTitulares:
    """Agrupa los documentos por titular y separa los grupos sin respaldo.

    Reglas aplicadas:
      - se agrupa por RUT; sin RUT, por nombre normalizado (palabras ordenadas,
        de modo que "SOTO PEREZ GLORIA ESTER" y "GLORIA ESTER SOTO PEREZ"
        sean el mismo titular);
      - un documento cuyo unico dato es un RUT de profesional (sin nombre) NO
        crea titular: el RUT del medico no identifica al paciente;
      - un RUT se acepta solo si esta declarado en la ficha del caso o si algun
        documento trae el nombre de ese RUT. Un RUT suelto no crea titular:
        puede ser el prestador, un acompanante o el paciente de otro bono del
        mismo talonario;
      - un nombre sin RUT se acepta si esta declarado en el caso o si aparece en
        al menos ``min_documentos`` documentos;
      - lo que no cumple va a ``descartados`` para reportarlo como advertencia;
      - los titulares declarados en la ficha del caso siempre aparecen, aunque
        todavia no tengan documentos.
    """
    config = config or []

    # Datos utiles por documento; se descartan los que no identifican a nadie.
    items: list[tuple[str | None, str | None]] = []
    for doc in documentos:
        rut = None if doc.titular_rut.is_empty else doc.titular_rut.value
        nombre = None if doc.titular_nombre.is_empty else doc.titular_nombre.value
        if not rut and not nombre:
            continue
        if rut and not nombre and _solo_rut_de_profesional(doc):
            continue
        items.append((rut, nombre))

    # Respaldo por clave y nombres que acompanan a cada RUT.
    soporte: dict[str, int] = {}
    nombre_por_rut: dict[str, str] = {}
    for rut, nombre in items:
        clave = f"rut:{rut_body(rut)}" if rut else f"nombre:{_name_key(nombre or '')}"
        soporte[clave] = soporte.get(clave, 0) + 1
        if rut and nombre:
            nombre_por_rut.setdefault(rut_body(rut), nombre)

    def _declarado(rut: str | None, nombre: str | None) -> bool:
        return any(item.matches(rut, nombre) for item in config)

    def _con_respaldo(rut: str | None, nombre: str | None, clave: str) -> bool:
        if _declarado(rut, nombre):
            return True
        if rut:
            # Un RUT sin nombre no identifica a nadie: puede ser el profesional,
            # un acompanante o el paciente de otro bono del mismo talonario. Solo
            # se acepta si algun documento trae el nombre de ese RUT o si esta
            # declarado en la ficha del caso (ver arriba).
            return rut_body(rut) in nombre_por_rut
        return soporte.get(clave, 0) >= min_documentos

    descartados: dict[str, tuple[Titular, int]] = {}

    # Fase 1: grupos con RUT. Se resuelven primero para que un documento que
    # solo trae el nombre se una al grupo correcto, sin importar el orden en
    # que llegaron los archivos.
    grupos: dict[str, Titular] = {}
    for rut, nombre in items:
        if not rut:
            continue
        clave = _titular_key(rut, nombre)
        if clave in grupos:
            continue
        if _con_respaldo(rut, nombre, clave):
            grupos[clave] = _nuevo_titular(rut, nombre, config)
        else:
            descartados.setdefault(
                clave, (Titular(rut=rut, nombre=nombre or ""), soporte.get(clave, 0))
            )

    # Fase 2: documentos sin RUT; se buscan por nombre contra los grupos ya
    # creados y entre si.
    for rut, nombre in items:
        if rut:
            continue
        clave = _buscar_por_nombre(nombre, grupos)
        if clave is None:
            clave = _titular_key(None, nombre)
            if clave not in grupos:
                if _con_respaldo(None, nombre, clave):
                    grupos[clave] = _nuevo_titular(None, nombre, config)
                else:
                    descartados.setdefault(
                        clave, (Titular(rut="", nombre=nombre or ""), soporte.get(clave, 0))
                    )
                continue
        titular = grupos[clave]
        # Se prefiere el nombre mas completo: "GLORIA ESTER SOTO PEREZ"
        # antes que el truncado "GLORIA ESTER SOT" que deja el OCR.
        if nombre and len(nombre) > len(titular.nombre):
            titular.nombre = nombre

    # Titulares declarados en el caso sin documentos propios (RUT pendiente).
    for item in config:
        if not item.nombre:
            continue
        if any(_name_key(t.nombre) == _name_key(item.nombre) for t in grupos.values() if t.nombre):
            continue
        if item.rut and any(rut_body(t.rut) == rut_body(item.rut) for t in grupos.values()):
            continue
        sin_documentos = all(
            assign_titular(doc, [Titular(rut=item.rut, nombre=item.nombre)]) is None
            for doc in documentos
        )
        if sin_documentos:
            grupos[_name_key(item.nombre)] = Titular(
                rut=item.rut or "", nombre=item.nombre, relacion=item.relacion, notas=item.notas
            )

    return AnalisisTitulares(
        titulares=sorted(grupos.values(), key=lambda t: (t.nombre or "zzz")),
        descartados=list(descartados.values()),
    )


def _solo_rut_de_profesional(doc: Document) -> bool:
    """True si el RUT del documento corresponde al profesional tratante."""
    if doc.profesional_rut.is_empty or doc.titular_rut.is_empty:
        return False
    return rut_body(doc.profesional_rut.value) == rut_body(doc.titular_rut.value)


def _nuevo_titular(
    rut: str | None, nombre: str | None, config: list[TitularConfig]
) -> Titular:
    """Crea un titular aplicando la ficha del caso cuando corresponde."""
    for item in config:
        if item.matches(rut, nombre):
            return Titular(
                rut=item.rut or rut or "",
                nombre=item.nombre or nombre or "",
                relacion=item.relacion,
            )
    return Titular(rut=rut or "", nombre=nombre or "")


def _buscar_por_nombre(nombre: str | None, grupos: dict[str, Titular]) -> str | None:
    """Clave del grupo cuyo nombre coincide con `nombre`, si existe.

    Primero se compara la clave normalizada (palabras ordenadas) y luego, solo
    contra grupos que tienen RUT verificado, una coincidencia por inclusion que
    tolera OCR truncado ("GLORIA ESTER SOT" vs "GLORIA ESTER SOTO PEREZ").
    """
    if not nombre:
        return None
    clave = _titular_key(None, nombre)
    if clave in grupos:
        return clave
    for otra_clave, titular in grupos.items():
        if titular.rut and titular.nombre and name_contains(titular.nombre, nombre):
            return otra_clave
    return None


def _titular_key(rut: str | None, nombre: str | None) -> str:
    """Clave de agrupacion: cuerpo del RUT o nombre con palabras ordenadas.

    Se usa el nombre ordenado para que el mismo titular escrito como
    "SOTO PEREZ GLORIA ESTER" (formato FONASA) y como "GLORIA ESTER SOTO
    PEREZ" (formato boleta) caiga en un unico grupo.
    """
    body = rut_body(rut)
    if body:
        return f"rut:{body}"
    return f"nombre:{_name_key(nombre or '')}"




def assign_titular(doc: Document, titulares: list[Titular]) -> Titular | None:
    """Devuelve el titular al que corresponde un documento.

    Si el titular declarado no tiene RUT, solo se acepta coincidencia exacta de
    nombre: asociar por coincidencia parcial sumaria montos a la persona
    equivocada, lo que en un informe para juicio es inaceptable.
    """
    rut = None if doc.titular_rut.is_empty else doc.titular_rut.value
    nombre = None if doc.titular_nombre.is_empty else doc.titular_nombre.value
    body = rut_body(rut)
    if body:
        for titular in titulares:
            if rut_body(titular.rut) == body:
                return titular
    if nombre:
        for titular in titulares:
            if _name_key(titular.nombre) == _name_key(nombre):
                return titular
        for titular in titulares:
            if titular.rut and name_contains(titular.nombre, nombre):
                return titular
    return None


def resolve_expediente(
    documentos: list[Document],
    carpeta: str,
    generado: str,
    config: list[TitularConfig] | None = None,
) -> Expediente:
    """Arma el expediente con titulares y advertencias de consistencia."""
    analisis = analizar_titulares(documentos, config)
    titulares = analisis.titulares
    advertencias: list[str] = []

    for titular, cuantos in analisis.descartados:
        etiqueta = titular.rut or titular.nombre or "sin datos"
        advertencias.append(
            f"Posible titular '{etiqueta}' aparece en {cuantos} documento(s) y no "
            "esta en la ficha del caso: no se incluyo como titular. "
            "Agreguelo a caso.json si corresponde."
        )

    for doc in documentos:
        if doc.titular_rut.confidence == CONF_FALTA:
            advertencias.append(
                f"{doc.doc_id}: sin RUT de titular identificado "
                f"({doc.source_file} p.{doc.page})"
            )
        titular = assign_titular(doc, titulares)
        if titular is None and doc.titular_nombre.value:
            advertencias.append(
                f"{doc.doc_id}: titular '{doc.titular_nombre.value}' no coincide con la "
                "lista de titulares declarada"
            )

    return Expediente(
        carpeta=carpeta,
        generado=generado,
        documentos=documentos,
        titulares=titulares,
        advertencias=advertencias,
    )

