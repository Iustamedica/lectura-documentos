"""Modalidad doctrina: libros, articulos, tesis y papers (un PDF = un item).

La ficha bibliografica se apoya en ``documental.biblioteca`` (titulo, autores,
ano, DOI, ISBN, idioma y paginas). El PDF se conserva entero: no se divide por
paginas ni se OCR-ea completo.
"""

from __future__ import annotations

import re

from ...classify import Classification
from ...models import CONF_ALTA, CONF_BAJA, CONF_MEDIA, Document, Field
from ...normalizers import fold
from ..base import CampoDef, Categoria, Perfil

CAT_LIBROS = "libros"
CAT_ARTICULOS = "articulos"
CAT_TESIS = "tesis"
CAT_PAPERS = "papers"
CAT_OTROS = "otros"

CATEGORIAS: tuple[Categoria, ...] = (
    Categoria(CAT_LIBROS, "Libros", "01-libros"),
    Categoria(CAT_ARTICULOS, "Articulos de revista", "02-articulos"),
    Categoria(CAT_TESIS, "Tesis y memorias", "03-tesis"),
    Categoria(CAT_PAPERS, "Papers y ponencias", "04-papers"),
    Categoria(CAT_OTROS, "Otras publicaciones", "05-otros"),
)

T_LIBRO = "Libro"
T_CAPITULO = "Capitulo de libro"
T_ARTICULO = "Articulo de revista"
T_TESIS = "Tesis o memoria"
T_PAPER = "Paper o ponencia"
T_PUBLICACION = "Publicacion de doctrina"

TIPOS: dict[str, str] = {
    T_LIBRO: CAT_LIBROS,
    T_CAPITULO: CAT_LIBROS,
    T_ARTICULO: CAT_ARTICULOS,
    T_TESIS: CAT_TESIS,
    T_PAPER: CAT_PAPERS,
    T_PUBLICACION: CAT_OTROS,
}

# Tipo que devuelve ``biblioteca._tipo`` -> tipo canonico de la modalidad.
DESDE_BIBLIOTECA: dict[str, str] = {
    "libro": T_LIBRO,
    "capitulo": T_CAPITULO,
    "articulo": T_ARTICULO,
    "tesis": T_TESIS,
    "memoria": T_TESIS,
    "material": T_PAPER,
    "informe": T_PUBLICACION,
    "publicacion": T_PUBLICACION,
}

CAMPOS: tuple[CampoDef, ...] = (
    CampoDef("autores", "Autores"),
    CampoDef("anio", "Ano"),
    CampoDef("tipo_publicacion", "Tipo de publicacion"),
    CampoDef("fuente", "Editorial o revista"),
    CampoDef("doi", "DOI"),
    CampoDef("isbn", "ISBN"),
    CampoDef("idioma", "Idioma"),
    CampoDef("paginas", "Paginas"),
)

_RE_ANIO = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_RE_DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+")
_RE_ISBN = re.compile(r"\b(?:97[89][\d\s-]{10,17}|\d{9}[\dXx])\b")



class PerfilDoctrina(Perfil):
    nombre = "doctrina"
    titulo_modalidad = "Doctrina"
    descripcion = "Libros, articulos, tesis y papers de una biblioteca juridica."

    categorias = CATEGORIAS
    campos = CAMPOS
    marcadores = (
        "isbn",
        "issn",
        "doi",
        "resumen",
        "palabras clave",
        "tesis para optar",
        "memoria para optar",
        "primera edicion",
        "derechos reservados",
    )
    tipo_ficha = ""
    tipo_sin_clasificar = T_PUBLICACION
    clave_fichas = ""
    titulo_informe = "CATALOGO DE DOCTRINA"
    etiqueta_titular = "Autor"
    usa_titulares = False
    usa_prestadores = False

    pistas_carpeta = (
        "doctrina",
        "biblioteca",
        "libros",
        "tesis",
        "articulos",
        "papers",
    )
    un_documento_por_pdf = True
    paginas_muestra_ocr = 0
    naturaleza_por_defecto = "doctrina"

    # -- clasificacion --------------------------------------------------
    def clasificar(self, texto: str) -> Classification:
        return Classification("doctrina", CONF_ALTA, {"doctrina": 10.0})

    def clasificar_naturaleza(self, texto: str) -> Classification:
        return Classification("doctrina", CONF_ALTA, {"doctrina": 10.0})

    def etiqueta_naturaleza(self, clave: str) -> str:
        return "Doctrina"

    def extractor(self, familia: str):
        from .extractores import extract_doctrina

        return extract_doctrina

    def tipo_canonico(self, documento: Document) -> str:
        declarado = str(documento.field("tipo_publicacion").value or "").strip()
        if declarado in TIPOS:
            return declarado
        texto = fold(documento.texto_ocr or "")
        if "tesis para optar" in texto or "tesis doctoral" in texto or "memoria para optar" in texto:
            return T_TESIS
        if "capitulo" in texto and ("pp." in texto or "en:" in texto):
            return T_CAPITULO
        if "doi" in texto or "issn" in texto or "revista" in texto:
            return T_ARTICULO
        if "isbn" in texto or "editorial" in texto:
            return T_LIBRO
        return T_PUBLICACION

    def categoria_de_tipo(self, tipo: str) -> str:
        return TIPOS.get(tipo, CAT_OTROS)

    def criticos_de(self, documento: Document) -> tuple[str, ...]:
        # La ficha bibliografica se revisa, pero no invalida el documento.
        return ()

    def columnas(self) -> tuple[tuple[str, str], ...]:
        return (
            ("N", "N"),
            ("categoria", "Coleccion"),
            ("tipo", "Tipo"),
            ("fecha", "Ano"),
            ("autores", "Autores"),
            ("fuente", "Editorial o revista"),
            ("detalle", "Referencia"),
        )

    def detalle_de(self, documento: Document) -> str:
        partes = [
            str(documento.field("doi").value or ""),
            str(documento.field("isbn").value or ""),
            str(documento.field("idioma").value or ""),
        ]
        paginas = documento.field("paginas").value
        if paginas:
            partes.append(f"{paginas} paginas")
        return ", ".join(parte for parte in partes if parte)

    # -- extraccion -----------------------------------------------------
    def refinar(self, documento: Document, prestadores: tuple | None = None) -> None:
        texto = documento.texto_ocr or ""
        folded = fold(texto)
        if documento.extra.get("anio", Field()).is_empty:
            anios = [int(valor) for valor in _RE_ANIO.findall(folded)]
            if anios:
                documento.extra["anio"] = Field(str(max(anios)), CONF_BAJA)
        if documento.extra.get("doi", Field()).is_empty:
            encontrado = _RE_DOI.search(texto)
            if encontrado:
                documento.extra["doi"] = Field(
                    encontrado.group(0), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("isbn", Field()).is_empty:
            encontrado = _RE_ISBN.search(texto)
            if encontrado:
                documento.extra["isbn"] = Field(
                    encontrado.group(0), CONF_MEDIA, encontrado.group(0)
                )
        if documento.extra.get("paginas", Field()).is_empty and documento.paginas:
            documento.extra["paginas"] = Field(str(len(documento.paginas)), CONF_ALTA)
        if documento.extra.get("tipo_publicacion", Field()).is_empty:
            documento.extra["tipo_publicacion"] = Field(
                self.tipo_canonico(documento), CONF_MEDIA
            )

    def enriquecer_completo(self, documento: Document, path) -> None:
        """Completa la ficha con la portada del PDF (sin OCR)."""
        try:
            from ...biblioteca import ficha_de

            ficha = ficha_de(path)
        except Exception:
            return
        if ficha.titulo:
            documento.titulo = ficha.titulo
        if ficha.autores:
            documento.extra["autores"] = Field(
                "; ".join(ficha.autores), _confianza(ficha.confianza_autores)
            )
        if ficha.anio:
            documento.extra["anio"] = Field(
                str(ficha.anio), _confianza(ficha.confianza_anio)
            )
            documento.fecha_emision.set(str(ficha.anio), CONF_MEDIA, ficha.fuente or "")
        if ficha.fuente:
            documento.extra["fuente"] = Field(ficha.fuente, CONF_MEDIA)
        if ficha.doi:
            documento.extra["doi"] = Field(ficha.doi, CONF_ALTA)
        if ficha.isbn:
            documento.extra["isbn"] = Field(ficha.isbn, CONF_ALTA)
        if ficha.idioma:
            documento.extra["idioma"] = Field(ficha.idioma, CONF_MEDIA)
        if ficha.paginas:
            documento.extra["paginas"] = Field(str(ficha.paginas), CONF_ALTA)
        tipo = DESDE_BIBLIOTECA.get(ficha.tipo, T_PUBLICACION)
        documento.extra["tipo_publicacion"] = Field(tipo, CONF_MEDIA)
        documento.tipo_documento.set(tipo, CONF_MEDIA)
        if ficha.notas:
            documento.observaciones.set(ficha.notas, CONF_BAJA)

    def texto_guia(self) -> str:
        return (
            "Coloque en esta carpeta los PDF de libros, articulos, tesis y papers.\n"
            "Cada PDF se conserva como un solo documento: no se divide por paginas.\n"
            "Luego ejecute 'Procesar documentos' (doble clic).\n"
        )


def _confianza(valor: str) -> str:
    """Convierte la confianza textual de la ficha al nivel del modelo."""
    valor = (valor or "").strip().lower()
    if valor in {CONF_ALTA, CONF_MEDIA, CONF_BAJA}:
        return valor
    return CONF_MEDIA
