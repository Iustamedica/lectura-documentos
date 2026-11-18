"""Modalidad jurisprudencia: sentencias de distintos tribunales.

Un PDF = una sentencia. La modalidad no divide el fallo por paginas y, si el
archivo es un escaneo, OCR-ea solo las primeras paginas para leer ROL, tribunal,
fecha y resultado.
"""

from __future__ import annotations

import re
from datetime import date

from ...classify import Classification
from ...models import CONF_ALTA, CONF_BAJA, CONF_MEDIA, Document, Field
from ...normalizers import fold, parse_date
from ..base import CampoDef, Categoria, Perfil

CAT_CORTE_SUPREMA = "corte_suprema"
CAT_CORTE_APELACIONES = "corte_apelaciones"
CAT_TRIBUNAL_CONSTITUCIONAL = "tribunal_constitucional"
CAT_TRIBUNALES_ESPECIALES = "tribunales_especiales"
CAT_OTROS = "otros"

CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(CAT_CORTE_SUPREMA, "Corte Suprema", "01-corte-suprema"),
    Categoria(CAT_CORTE_APELACIONES, "Cortes de Apelaciones", "02-corte-apelaciones"),
    Categoria(
        CAT_TRIBUNAL_CONSTITUCIONAL,
        "Tribunal Constitucional",
        "03-tribunal-constitucional",
    ),
    Categoria(
        CAT_TRIBUNALES_ESPECIALES,
        "Tribunales especiales",
        "04-tribunales-especiales",
    ),
    Categoria(CAT_OTROS, "Otras sentencias", "05-otros"),
)

T_CS = "Sentencia de la Corte Suprema"
T_CA = "Sentencia de Corte de Apelaciones"
T_TC = "Sentencia del Tribunal Constitucional"
T_TRIBUNAL = "Sentencia de tribunal"
T_AUTO = "Auto o resolucion judicial"
T_SIN = "Sentencia sin clasificar"

TIPOS: dict[str, str] = {
    T_CS: CAT_CORTE_SUPREMA,
    T_CA: CAT_CORTE_APELACIONES,
    T_TC: CAT_TRIBUNAL_CONSTITUCIONAL,
    T_TRIBUNAL: CAT_TRIBUNALES_ESPECIALES,
    T_AUTO: CAT_OTROS,
    T_SIN: CAT_OTROS,
}

CAMPOS: tuple[CampoDef, ...] = (
    CampoDef("rol", "ROL / RIT", True),
    CampoDef("tribunal", "Tribunal", True),
    CampoDef("sala", "Sala"),
    CampoDef("caratula", "Caratula"),
    CampoDef("materia", "Materia"),
    CampoDef("tipo_sentencia", "Tipo de sentencia"),
    CampoDef("redactor", "Redactor"),
    CampoDef("resultado", "Resultado"),
    CampoDef("fecha_emision", "Fecha", True),
)

_RE_ROL = re.compile(
    r"\b(?:rol|rit)\s*(?:n[.\u00ba\u00b0]?\s*)?([a-z]{0,3}[- ]?\d{1,6}[- ]?\d{2,4})\b",
    re.IGNORECASE,
)
_RE_CARATULA = re.compile(r"caratula\s*[:\-]?\s*([^\n]{3,120})", re.IGNORECASE)
_RE_REDACTOR = re.compile(r"redactor\s*[:\-]?\s*([^\n]{3,80})", re.IGNORECASE)
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



class PerfilJurisprudencia(Perfil):
    nombre = "jurisprudencia"
    titulo_modalidad = "Jurisprudencia"
    descripcion = "Sentencias de la Corte Suprema, Cortes de Apelaciones y TC."

    categorias = CATEGORIAS
    campos = CAMPOS
    marcadores = (
        "vistos",
        "considerando",
        "resuelvo",
        "se confirma la sentencia",
        "se revoca la sentencia",
        "sentencia de reemplazo",
    )
    tipo_ficha = ""
    tipo_sin_clasificar = T_SIN
    clave_fichas = ""
    titulo_informe = "INFORME DE JURISPRUDENCIA"
    etiqueta_titular = "Tribunal"
    usa_titulares = False
    usa_prestadores = False

    pistas_carpeta = (
        "jurisprudencia",
        "sentencias",
        "fallos",
        "corte suprema",
        "corte de apelaciones",
        "tribunal constitucional",
    )
    un_documento_por_pdf = True
    paginas_muestra_ocr = 4
    naturaleza_por_defecto = "jurisprudencia"

    # -- clasificacion --------------------------------------------------
    def clasificar(self, texto: str) -> Classification:
        folded = fold(texto)
        if "auto" in folded and "sentencia" not in folded:
            return Classification("auto", CONF_MEDIA, {"auto": 3.0})
        return Classification("sentencia", CONF_ALTA, {"sentencia": 6.0})

    def clasificar_naturaleza(self, texto: str) -> Classification:
        return Classification("jurisprudencia", CONF_ALTA, {"jurisprudencia": 8.0})

    def etiqueta_naturaleza(self, clave: str) -> str:
        return "Jurisprudencia"

    def etiqueta_familia(self, familia: str) -> str:
        return "Auto" if familia == "auto" else "Sentencia"

    def extractor(self, familia: str):
        from .extractores import extract_jurisprudencia

        return extract_jurisprudencia

    def tipo_canonico(self, documento: Document) -> str:
        texto = fold(documento.texto_ocr or "")
        if "auto" in texto and "sentencia" not in texto:
            return T_AUTO
        if "tribunal constitucional" in texto:
            return T_TC
        if "corte suprema" in texto:
            return T_CS
        if "corte de apelaciones" in texto:
            return T_CA
        if "tribunal" in texto or "juzgado" in texto:
            return T_TRIBUNAL
        return T_SIN

    def categoria_de_tipo(self, tipo: str) -> str:
        return TIPOS.get(tipo, CAT_OTROS)

    def criticos_de(self, documento: Document) -> tuple[str, ...]:
        return ("rol", "tribunal", "fecha_emision")

    def columnas(self) -> tuple[tuple[str, str], ...]:
        return (
            ("N", "N"),
            ("categoria", "Tribunal"),
            ("tipo", "Tipo"),
            ("fecha", "Fecha"),
            ("rol", "ROL"),
            ("tribunal", "Tribunal"),
            ("sala", "Sala"),
            ("caratula", "Caratula"),
            ("resultado", "Resultado"),
            ("detalle", "Detalle"),
        )

    def detalle_de(self, documento: Document) -> str:
        partes = [
            str(documento.field("materia").value or ""),
            str(documento.field("redactor").value or ""),
        ]
        return ", ".join(parte for parte in partes if parte)

    # -- extraccion -----------------------------------------------------
    def refinar(self, documento: Document, prestadores: tuple | None = None) -> None:
        texto = documento.texto_ocr or ""
        folded = fold(texto)
        if documento.extra.get("rol", Field()).is_empty:
            encontrado = _RE_ROL.search(texto)
            if encontrado:
                documento.extra["rol"] = Field(
                    _limpiar_rol(encontrado.group(1)), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("tribunal", Field()).is_empty:
            tribunal = _tribunal(folded)
            if tribunal:
                documento.extra["tribunal"] = Field(tribunal, CONF_MEDIA)
        if documento.extra.get("sala", Field()).is_empty:
            sala = _sala(folded)
            if sala:
                documento.extra["sala"] = Field(sala, CONF_MEDIA)
        if documento.fecha_emision.is_empty:
            fecha = _fecha(texto)
            if fecha:
                documento.fecha_emision.set(fecha.isoformat(), CONF_MEDIA)
        if documento.extra.get("caratula", Field()).is_empty:
            encontrado = _RE_CARATULA.search(texto)
            if encontrado:
                documento.extra["caratula"] = Field(
                    encontrado.group(1).strip(), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("redactor", Field()).is_empty:
            encontrado = _RE_REDACTOR.search(texto)
            if encontrado:
                documento.extra["redactor"] = Field(
                    encontrado.group(1).strip(), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("resultado", Field()).is_empty:
            resultado = _resultado(folded)
            if resultado:
                documento.extra["resultado"] = Field(resultado, CONF_MEDIA)
        if documento.extra.get("tipo_sentencia", Field()).is_empty:
            documento.extra["tipo_sentencia"] = Field(
                self.tipo_canonico(documento), CONF_MEDIA
            )

    def texto_guia(self) -> str:
        return (
            "Coloque en esta carpeta las sentencias (un PDF por fallo).\n"
            "Cada PDF se conserva como un solo documento; si es un escaneo se\n"
            "OCR-ean solo las primeras paginas para leer ROL, tribunal y fecha.\n"
            "Luego ejecute 'Procesar documentos' (doble clic).\n"
        )


def _limpiar_rol(valor: str) -> str:
    return re.sub(r"\s+", " ", (valor or "").strip()).upper()


def _tribunal(folded: str) -> str:
    if "tribunal constitucional" in folded:
        return "Tribunal Constitucional"
    if "corte suprema" in folded:
        return "Corte Suprema"
    encontrado = re.search(r"corte de apelaciones de ([a-z ]{3,40})", folded)
    if encontrado:
        return "Corte de Apelaciones de " + encontrado.group(1).strip().title()
    encontrado = re.search(r"(juzgado de letras[^\n]{0,60})", folded)
    if encontrado:
        return encontrado.group(1).strip().title()
    return ""


def _sala(folded: str) -> str:
    encontrado = re.search(
        r"sala (primera|segunda|tercera|cuarta|constitucional|penal|civil|laboral)",
        folded,
    )
    if encontrado:
        return "Sala " + encontrado.group(1).title()
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
    return parse_date(texto[:400])


def _fecha_segura(anio: int, mes: int, dia: int) -> date | None:
    try:
        return date(anio, mes, dia)
    except ValueError:
        return None


def _resultado(folded: str) -> str:
    if "se confirma la sentencia" in folded or "confirma la sentencia" in folded:
        return "Confirma"
    if "se revoca la sentencia" in folded or "revoca la sentencia" in folded:
        return "Revoca"
    if "acoge" in folded:
        return "Acoge"
    if "rechaza" in folded:
        return "Rechaza"
    return ""
