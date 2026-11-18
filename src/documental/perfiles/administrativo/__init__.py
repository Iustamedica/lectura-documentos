"""Modalidad actos administrativos: resoluciones y dictamenes de la Administracion.

Incluye Contraloria General de la Republica, Superintendencias, ministerios,
municipalidades y otros organos publicos. Un PDF = un acto.
"""

from __future__ import annotations

import re
from datetime import date

from ...classify import Classification
from ...models import CONF_ALTA, CONF_MEDIA, Document, Field
from ...normalizers import fold
from ..base import CampoDef, Categoria, Perfil

CAT_CONTRALORIA = "contraloria"
CAT_SUPERINTENDENCIA = "superintendencia_salud"
CAT_MINISTERIOS = "ministerios"
CAT_MUNICIPALIDADES = "municipalidades"
CAT_OTROS = "otros"

CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(CAT_CONTRALORIA, "Contraloria", "01-contraloria"),
    Categoria(CAT_SUPERINTENDENCIA, "Superintendencia de Salud", "02-superintendencia-salud"),
    Categoria(CAT_MINISTERIOS, "Ministerios", "03-ministerios"),
    Categoria(CAT_MUNICIPALIDADES, "Municipalidades", "04-municipalidades"),
    Categoria(CAT_OTROS, "Otros actos", "05-otros"),
)

T_RES_EXENTA = "Resolucion exenta"
T_RES_AFECTA = "Resolucion afecta"
T_DICTAMEN = "Dictamen"
T_OFICIO = "Oficio"
T_SANCION = "Sancion administrativa"
T_ACTO = "Acto administrativo"

TIPOS: dict[str, str] = {
    T_RES_EXENTA: CAT_OTROS,
    T_RES_AFECTA: CAT_OTROS,
    T_DICTAMEN: CAT_CONTRALORIA,
    T_OFICIO: CAT_OTROS,
    T_SANCION: CAT_OTROS,
    T_ACTO: CAT_OTROS,
}

CAMPOS: tuple[CampoDef, ...] = (
    CampoDef("institucion", "Institucion", True),
    CampoDef("numero", "Numero del acto", True),
    CampoDef("fecha_emision", "Fecha", True),
    CampoDef("materia", "Materia"),
    CampoDef("destinatario", "Destinatario"),
    CampoDef("tipo_acto", "Tipo de acto"),
    CampoDef("estado", "Estado"),
)

_RE_NUMERO = re.compile(
    r"\b(?:resolucion|res\.?|dictamen|ordinario|ord\.?|oficio)\s*"
    r"(?:exenta|afecta|ex\.?|af\.?)?\s*(?:n[.\u00ba\u00b0]?\s*)?([\d][\d.\-]{2,20})",
    re.IGNORECASE,
)
_RE_MATERIA = re.compile(r"materia\s*[:\-]\s*([^\n]{3,160})", re.IGNORECASE)
_RE_DESTINATARIO = re.compile(
    r"(?:destinatario|a\s*:)\s*([^\n]{3,120})", re.IGNORECASE
)
_RE_FECHA_NUM = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")
_RE_FECHA_TEXTO = re.compile(
    r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|"
    r"septiembre|setiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",
    re.IGNORECASE,
)
_MESES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}



class PerfilAdministrativo(Perfil):
    nombre = "administrativo"
    titulo_modalidad = "Actos administrativos"
    descripcion = "Resoluciones, dictamenes y oficios de organos publicos."

    categorias = CATEGORIAS
    campos = CAMPOS
    marcadores = (
        "resolucion exenta",
        "resolucion afecta",
        "dictamen",
        "contraloria general de la republica",
        "superintendencia",
        "ministerio de",
        "municipalidad de",
    )
    tipo_ficha = ""
    tipo_sin_clasificar = T_ACTO
    clave_fichas = ""
    titulo_informe = "INFORME DE ACTOS ADMINISTRATIVOS"
    etiqueta_titular = "Institucion"
    usa_titulares = False
    usa_prestadores = False

    pistas_carpeta = (
        "actos administrativos",
        "acto administrativo",
        "resoluciones administrativas",
        "contraloria",
        "superintendencia",
        "ministerios",
        "municipalidades",
    )
    un_documento_por_pdf = True
    paginas_muestra_ocr = 4
    naturaleza_por_defecto = "resolucion"

    # -- clasificacion --------------------------------------------------
    def clasificar(self, texto: str) -> Classification:
        return Classification("resolucion", CONF_ALTA, {"resolucion": 6.0})

    def clasificar_naturaleza(self, texto: str) -> Classification:
        return Classification("resolucion", CONF_ALTA, {"resolucion": 8.0})

    def etiqueta_naturaleza(self, clave: str) -> str:
        return "Acto administrativo"

    def etiqueta_familia(self, familia: str) -> str:
        return "Acto administrativo"

    def extractor(self, familia: str):
        from .extractores import extract_administrativo

        return extract_administrativo

    def tipo_canonico(self, documento: Document) -> str:
        texto = fold(documento.texto_ocr or "")
        institucion = _institucion(texto)
        if "dictamen" in texto:
            base = T_DICTAMEN
        elif "sancion" in texto or "multa" in texto:
            base = T_SANCION
        elif "resolucion exenta" in texto:
            base = T_RES_EXENTA
        elif "resolucion afecta" in texto or "resolucion" in texto:
            base = T_RES_AFECTA
        elif "oficio" in texto or "ordinario" in texto:
            base = T_OFICIO
        else:
            base = T_ACTO
        if institucion:
            return f"{base} - {institucion}"
        return base

    def categoria_de_tipo(self, tipo: str) -> str:
        folded = fold(tipo)
        if "contraloria" in folded:
            return CAT_CONTRALORIA
        if "superintendencia" in folded:
            return CAT_SUPERINTENDENCIA
        if "ministerio" in folded:
            return CAT_MINISTERIOS
        if "municipalidad" in folded:
            return CAT_MUNICIPALIDADES
        return CAT_OTROS

    def criticos_de(self, documento: Document) -> tuple[str, ...]:
        return ("institucion", "numero", "fecha_emision")

    def columnas(self) -> tuple[tuple[str, str], ...]:
        return (
            ("N", "N"),
            ("categoria", "Institucion"),
            ("tipo", "Tipo de acto"),
            ("fecha", "Fecha"),
            ("institucion", "Institucion"),
            ("numero", "Numero"),
            ("materia", "Materia"),
            ("destinatario", "Destinatario"),
            ("detalle", "Detalle"),
        )

    def detalle_de(self, documento: Document) -> str:
        partes = [
            str(documento.field("estado").value or ""),
            str(documento.field("tipo_acto").value or ""),
        ]
        return ", ".join(parte for parte in partes if parte)

    # -- extraccion -----------------------------------------------------
    def refinar(self, documento: Document, prestadores: tuple | None = None) -> None:
        texto = documento.texto_ocr or ""
        folded = fold(texto)
        if documento.extra.get("institucion", Field()).is_empty:
            institucion = _institucion(folded)
            if institucion:
                documento.extra["institucion"] = Field(institucion, CONF_MEDIA)
        if documento.extra.get("numero", Field()).is_empty:
            encontrado = _RE_NUMERO.search(texto)
            if encontrado:
                documento.extra["numero"] = Field(
                    encontrado.group(1).strip(" .-"), CONF_MEDIA, encontrado.group(0)
                )
        if documento.fecha_emision.is_empty:
            fecha = _fecha(texto)
            if fecha:
                documento.fecha_emision.set(fecha.isoformat(), CONF_MEDIA)
        if documento.extra.get("materia", Field()).is_empty:
            encontrado = _RE_MATERIA.search(texto)
            if encontrado:
                documento.extra["materia"] = Field(
                    encontrado.group(1).strip(), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("destinatario", Field()).is_empty:
            encontrado = _RE_DESTINATARIO.search(texto)
            if encontrado:
                documento.extra["destinatario"] = Field(
                    encontrado.group(1).strip(), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("tipo_acto", Field()).is_empty:
            documento.extra["tipo_acto"] = Field(
                self.tipo_canonico(documento), CONF_MEDIA
            )
        if documento.extra.get("estado", Field()).is_empty:
            estado = _estado(folded)
            if estado:
                documento.extra["estado"] = Field(estado, CONF_MEDIA)

    def texto_guia(self) -> str:
        return (
            "Coloque en esta carpeta las resoluciones, dictamenes y oficios\n"
            "(un PDF por acto). Cada PDF se conserva como un solo documento.\n"
            "Luego ejecute 'Procesar documentos' (doble clic).\n"
        )


def _institucion(folded: str) -> str:
    if "contraloria general de la republica" in folded or "contraloria" in folded:
        return "Contraloria General de la Republica"
    if "superintendencia de salud" in folded:
        return "Superintendencia de Salud"
    encontrado = re.search(r"superintendencia de ([a-z ]{3,40})", folded)
    if encontrado:
        return "Superintendencia de " + encontrado.group(1).strip().title()
    encontrado = re.search(r"ministerio de ([a-z ]{3,50})", folded)
    if encontrado:
        return "Ministerio de " + encontrado.group(1).strip().title()
    encontrado = re.search(r"municipalidad de ([a-z ]{3,50})", folded)
    if encontrado:
        return "Municipalidad de " + encontrado.group(1).strip().title()
    return ""


def _fecha(texto: str) -> date | None:
    encontrado = _RE_FECHA_NUM.search(texto)
    if encontrado:
        dia, mes, anio = (int(parte) for parte in encontrado.groups())
        return _fecha_segura(anio, mes, dia)
    encontrado = _RE_FECHA_TEXTO.search(texto)
    if encontrado:
        dia = int(encontrado.group(1))
        mes = _MESES.get(fold(encontrado.group(2)), 0)
        anio = int(encontrado.group(3))
        return _fecha_segura(anio, mes, dia)
    return None


def _fecha_segura(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _estado(folded: str) -> str:
    if "tramite" in folded:
        return "En tramite"
    if "notificada" in folded:
        return "Notificada"
    if "archiv" in folded:
        return "Archivada"
    return ""
