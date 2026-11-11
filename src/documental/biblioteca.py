"""Modo biblioteca: ficha de cada PDF de doctrina, sin partir el documento.

A diferencia del flujo de expedientes, aqui **un PDF es un item**: no se separa
por paginas ni se buscan partes procesales. Se extrae la ficha bibliografica que
permita catalogar y ordenar la biblioteca:

    titulo, autores, anio, tipo, fuente, doi, isbn, idioma, paginas

La extraccion es heuristica y local: portada (bloque de mayor tamano), pagina de
copyright, metadatos del PDF y, como respaldo, el nombre del archivo. Cada campo
lleva su nivel de confianza para que el catalogo se pueda revisar.

Opcionalmente reordena las paginas por el numero impreso (ver
``ordenar_paginas``) y escribe un PDF nuevo; nunca modifica el original.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

import pymupdf

from .normalizers import fold
from .ordenar_paginas import ordenar_pdf

_RE_DOI = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+")
_RE_ISBN = re.compile(r"\b(?:97[89][\d\s-]{10,17}|\d{9}[\dXx])\b")
_RE_ANIO_EDICION = re.compile(
    r"(?:primera|segunda|tercera|cuarta|quinta|\d+\.?ª?)\s+edici[oó]n"
    r"[^\d]{0,40}(\d{4})",
    re.IGNORECASE,
)
_RE_ANIO_COPY = re.compile(r"(?:©|copyright|derechos reservados)[^\d]{0,20}(\d{4})", re.IGNORECASE)
_RE_ANIO_SUELTO = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")

_INSTITUCIONES = (
    "universidad", "facultad", "escuela", "departamento", "instituto", "centro",
    "programa", "editorial", "revista", "comision", "comisión", "ministerio",
    "corte", "tribunal", "gobierno", "municipalidad", "colegio", "academia",
    "serie", "coleccion", "colección", "memoria", "tesis", "informe", "derechos",
    "reservados", "isbn", "issn", "doi", "vol", "num", "paginas", "páginas",
)

_STOP_ES = (
    " de la que el en y a los se del las un por con no una su para es al lo "
    "como mas más pero sus le ya o este si sí porque esta entre cuando muy sin "
    "sobre tambien también me hasta hay donde quien desde todo nos durante "
    "todos uno les ni contra otros ese eso ante ellos e esto mi mí antes "
    "algunos que unos yo otro otras otra el tanto esa estos mucho quienes nada "
    "muchos cual poco ella estar estas algunas algo nosotros"
).split()
_STOP_EN = (
    " the of and to in a is that for it as with was on be by this are or from "
    "at an not have has but which their its can will would there been more"
).split()

_TITULO_BASURA = (
    "pdf.js viewer", "about:blank", "pagina 1 de", "página 1 de",
)

# Encabezados que pueden ser el texto mas grande de la pagina pero no son titulo.
_TITULO_EXACTO = {
    "doctrina", "contenidos", "indice", "índice", "sumario", "portada",
    "introduccion", "introducción", "escuela de derecho",
    "departamento de derecho", "material y metodo", "material y método",
}

_AUTOR_BASURA = (
    "palabras clave", "key words", "resumen", "abstract", "material", "metodo",
    "método", "introduccion", "introducción", "contenidos", "doi", "isbn", "issn",
    "revista", "universidad", "facultad", "departamento", "escuela", "doctrina",
    "capitulo", "capítulo", "seccion", "sección", "pagina", "página", "volumen",
    "numero", "número", "elsevier", "thomson", "tirant", "lexis", "santiago",
    "chile", "valparaiso", "valparaíso", "concepcion", "concepción", "estudio",
    "real", "pdf.js",
)

_MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
)


@dataclass
class Ficha:
    """Ficha bibliografica de un PDF de doctrina."""

    archivo: str
    ruta: str
    md5: str = ""
    paginas: int = 0
    titulo: str = ""
    autores: list[str] = field(default_factory=list)
    anio: int | None = None
    tipo: str = "publicacion"
    fuente: str = ""
    doi: str = ""
    isbn: str = ""
    idioma: str = ""
    confianza_titulo: str = "baja"
    confianza_autores: str = "baja"
    confianza_anio: str = "baja"
    reordenado: bool = False
    orden_motivo: str = ""
    orden_informe: list[dict] = field(default_factory=list)
    notas: str = ""

    @property
    def autores_texto(self) -> str:
        return "; ".join(self.autores)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["autores"] = list(self.autores)
        return data


def _md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _isbn_valido(texto: str) -> bool:
    digitos = re.sub(r"[^0-9Xx]", "", texto).upper()
    if len(digitos) == 13 and digitos.isdigit():
        suma = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digitos))
        return suma % 10 == 0
    if len(digitos) == 10:
        try:
            suma = sum(
                (10 - i) * (10 if c == "X" else int(c)) for i, c in enumerate(digitos)
            )
        except ValueError:
            return False
        return suma % 11 == 0
    return False


def _anio_valido(anio: int | None) -> bool:
    if not anio:
        return False
    return 1900 <= anio <= datetime.now().year + 1


def _titulo(doc: pymupdf.Document) -> tuple[str, str]:
    """Titulo: bloque de mayor tamano de fuente en las primeras paginas."""
    mejor: tuple[float, str] | None = None
    for indice in range(min(3, doc.page_count)):
        data = doc[indice].get_text("dict")
        for bloque in data.get("blocks", []):
            if bloque.get("type") != 0:
                continue
            lineas: list[str] = []
            tamano = 0.0
            for linea in bloque.get("lines", []):
                spans = linea.get("spans", [])
                texto = "".join(span.get("text", "") for span in spans).strip()
                if not texto:
                    continue
                lineas.append(texto)
                tamano = max(tamano, max((span.get("size", 0) for span in spans), default=0))
            candidato = " ".join(lineas).strip()
            if not 8 <= len(candidato) <= 300:
                continue
            if re.fullmatch(r"[\d\s|.,;:-]+", candidato):
                continue
            folded = fold(candidato)
            if (
                any(basura in folded for basura in _TITULO_BASURA)
                or folded.strip() in _TITULO_EXACTO
            ):
                continue
            if len(candidato) < 120 and folded.startswith(
                ("universidad", "facultad", "pontificia", "revista", "editorial",
                 "comision", "ministerio", "corte", "tribunal", "isbn", "issn")
            ):
                continue
            if mejor is None or tamano > mejor[0]:
                mejor = (tamano, candidato)
    if mejor:
        return mejor[1], "alta"

    for indice in range(min(3, doc.page_count)):
        for linea in doc[indice].get_text().splitlines():
            linea = linea.strip()
            folded_linea = fold(linea)
            if (
                any(basura in folded_linea for basura in _TITULO_BASURA)
                or folded_linea.strip() in _TITULO_EXACTO
            ):
                continue
            if len(linea) >= 12 and not re.fullmatch(r"[\d\s|.,;:-]+", linea):
                return linea, "media"
    return "", "baja"


def _titulo_desde_archivo(path: Path) -> str:
    """Titulo legible a partir del nombre: 2019_autor_titulo_fuente.pdf."""
    tallo = re.sub(r"^\d{4}[-_]", "", path.stem)
    partes = [parte for parte in tallo.split("_") if parte]
    if len(partes) >= 3:
        partes = partes[:-1]
    texto = " ".join(partes).replace("-", " ")
    texto = re.sub(r"\s+", " ", texto).strip()
    return (texto[:1].upper() + texto[1:]) if texto else ""


def _autores(textos: list[str], titulo: str) -> tuple[list[str], str]:
    """Autores: linea explicita ("por", "Autor:") o nombres bajo el titulo."""
    plano = " ".join(textos)
    encontrado = re.search(
        r"(?:autores?)\s*:?\s*([A-ZÁÉÍÓÚÑ][^.;\n]{5,120})", plano
    )
    if encontrado:
        candidatos = re.split(r",|;| y ", encontrado.group(1))
        limpios = [_limpiar_autor(item) for item in candidatos]
        validos = [item for item in limpios if _parece_nombre(item)]
        if validos:
            return validos[:4], "alta"

    patron = re.compile(
        r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+(?:\s+(?:de|del|la|los|las|y)?\s*"
        r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+){1,3}$"
    )
    candidatos: list[str] = []
    for linea in textos:
        limpia = linea.strip().strip(".,;")
        if limpia == titulo or len(limpia) < 6 or len(limpia) > 70:
            continue
        if patron.match(limpia) and _parece_nombre(limpia):
            candidatos.append(limpia)
    unicos: list[str] = []
    for nombre in candidatos:
        if nombre not in unicos:
            unicos.append(nombre)
    if unicos:
        return unicos[:4], "media"
    return [], "baja"


def _limpiar_autor(texto: str) -> str:
    limpio = re.sub(r"\s+", " ", texto).strip(" .,;:-")
    limpio = re.sub(
        r"^(?:dr|dra|prof|profesor|profesora|sr|sra)\.?\s+", "", limpio, flags=re.I
    )
    return limpio


def _parece_nombre(texto: str) -> bool:
    folded = fold(texto)
    if not texto or len(texto) > 70:
        return False
    if any(basura in folded for basura in _AUTOR_BASURA):
        return False
    if any(palabra in folded for palabra in _INSTITUCIONES):
        return False
    if any(mes in folded for mes in _MESES):
        return False
    palabras = texto.split()
    if not 2 <= len(palabras) <= 5:
        return False
    return all(
        re.fullmatch(r"[A-Za-zÁÉÍÓÚÑáéíóúñü'.-]+", palabra) for palabra in palabras
    )


def _anio(textos: str, metadata: dict, archivo: Path) -> tuple[int | None, str]:
    for patron in (_RE_ANIO_EDICION, _RE_ANIO_COPY):
        encontrado = patron.search(textos)
        if encontrado and _anio_valido(int(encontrado.group(1))):
            return int(encontrado.group(1)), "alta"
    # El nombre del archivo suele ser el año de publicacion, no el de una cita.
    en_nombre = re.match(r"^(\d{4})[-_]", archivo.name)
    if en_nombre and _anio_valido(int(en_nombre.group(1))):
        return int(en_nombre.group(1)), "media"
    fecha = (metadata or {}).get("creationDate", "")
    creado = re.search(r"D:(\d{4})", fecha)
    if creado and _anio_valido(int(creado.group(1))):
        return int(creado.group(1)), "media"
    suelto = _RE_ANIO_SUELTO.search(textos)
    if suelto:
        return int(suelto.group(1)), "baja"
    return None, "baja"


def _doi(texto: str) -> str:
    encontrado = _RE_DOI.search(texto)
    return encontrado.group(0).rstrip(".,;)]}") if encontrado else ""


def _isbn(texto: str) -> str:
    for encontrado in _RE_ISBN.finditer(texto):
        if _isbn_valido(encontrado.group(0)):
            return re.sub(r"[^0-9Xx]", "", encontrado.group(0)).upper()
    return ""


def _tipo(texto: str, doi: str, isbn: str) -> str:
    folded = fold(texto)
    if "tesis para optar" in folded or "tesis doctoral" in folded:
        return "tesis"
    if "memoria para optar" in folded:
        return "memoria"
    if "materiales docentes" in folded:
        return "material"
    if "capitulo" in folded and ("pp." in folded or "en:" in folded):
        return "capitulo"
    if doi or "issn" in folded or "revista" in folded:
        return "articulo"
    if isbn:
        return "libro"
    if "informe" in folded:
        return "informe"
    return "publicacion"


def _fuente(texto: str) -> str:
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not 4 <= len(limpia) <= 120:
            continue
        if re.match(
            r"(?i)^(revista|gaceta|editorial|universidad|facultad|serie|coleccion)\b",
            limpia,
        ):
            return limpia[:110]
    return ""


def _idioma(texto: str) -> str:
    folded = fold(texto)
    espanol = sum(
        1 for palabra in _STOP_ES if re.search(rf"\b{re.escape(palabra)}\b", folded)
    )
    ingles = sum(
        1 for palabra in _STOP_EN if re.search(rf"\b{re.escape(palabra)}\b", folded)
    )
    return "es" if espanol >= ingles else "en"


def ficha_de(
    path: Path,
    *,
    reordenar: bool = False,
    salida: Path | None = None,
) -> Ficha:
    """Extrae la ficha bibliografica de un PDF (un item = un PDF)."""
    path = Path(path)
    with pymupdf.open(str(path)) as doc:
        paginas = doc.page_count
        textos_paginas = [doc[indice].get_text() for indice in range(min(5, paginas))]
        metadata = doc.metadata or {}
        titulo, confianza_titulo = _titulo(doc)

    texto = "\n".join(textos_paginas)
    lineas = [
        linea.strip() for bloque in textos_paginas for linea in bloque.splitlines()
        if linea.strip()
    ]
    folded_titulo = fold(titulo)
    if (
        not titulo
        or any(basura in folded_titulo for basura in _TITULO_BASURA)
        or folded_titulo.strip() in _TITULO_EXACTO
    ):
        alternativo = _titulo_desde_archivo(path)
        if alternativo:
            titulo = alternativo
            confianza_titulo = "media"
    if not titulo:
        titulo = path.stem.replace("_", " ").replace("-", " ").strip()
        confianza_titulo = "baja"
    autores, confianza_autores = _autores(lineas, titulo)
    anio, confianza_anio = _anio(texto, metadata, path)
    doi = _doi(texto)
    isbn = _isbn(texto)

    ficha = Ficha(
        archivo=path.name,
        ruta=str(path.resolve()),
        md5=_md5(path),
        paginas=paginas,
        titulo=titulo,
        autores=autores,
        anio=anio,
        tipo=_tipo(texto, doi, isbn),
        fuente=_fuente(texto),
        doi=doi,
        isbn=isbn,
        idioma=_idioma(texto),
        confianza_titulo=confianza_titulo,
        confianza_autores=confianza_autores,
        confianza_anio=confianza_anio,
    )
    if not texto.strip():
        ficha.notas = "sin capa de texto: requiere OCR para extraer la ficha"

    if reordenar:
        destino = Path(salida) / f"{path.stem}-ordenado.pdf" if salida else None
        resultado = ordenar_pdf(path, destino)
        ficha.reordenado = resultado.reordenado
        ficha.orden_motivo = resultado.motivo
        ficha.orden_informe = resultado.informe()
    return ficha


def catalogo(
    carpeta: Path,
    *,
    reordenar: bool = False,
    salida: Path | None = None,
    renombrar: bool = False,
) -> list[Ficha]:
    """Recorre una carpeta y devuelve la ficha de cada PDF."""
    carpeta = Path(carpeta)
    if salida is not None:
        Path(salida).mkdir(parents=True, exist_ok=True)
    archivos = sorted(
        path
        for path in carpeta.rglob("*.pdf")
        if path.is_file() and "-ordenado" not in path.stem
    )
    fichas: list[Ficha] = []
    for path in archivos:
        ficha = ficha_de(path, reordenar=reordenar, salida=salida)
        if renombrar and salida is not None:
            copia = Path(salida) / _nombre_archivo(ficha)
            contador = 1
            while copia.exists():
                contador += 1
                copia = copia.with_name(f"{copia.stem}-{contador}{copia.suffix}")
            shutil.copy2(path, copia)
            ficha.notas = (ficha.notas + " | copia renombrada").strip(" |")
        fichas.append(ficha)
    return fichas


def _slug(texto: str, maximo: int = 60) -> str:
    limpio = re.sub(r"[^a-z0-9]+", "-", fold(texto or "")).strip("-")
    return limpio[:maximo].strip("-") or "sin-titulo"


def _nombre_archivo(ficha: Ficha) -> str:
    autor = _slug(ficha.autores[0].split()[-1], 30) if ficha.autores else "anon"
    partes = [
        str(ficha.anio or "0000"),
        autor,
        _slug(ficha.titulo),
        _slug(ficha.fuente, 30) if ficha.fuente else "",
    ]
    return "_".join(parte for parte in partes if parte) + ".pdf"


COLUMNAS = (
    "archivo", "ruta", "md5", "paginas", "titulo", "autores", "anio", "tipo",
    "fuente", "doi", "isbn", "idioma", "confianza_titulo", "confianza_autores",
    "confianza_anio", "reordenado", "orden_motivo", "notas",
)


def escribir_catalogo(
    fichas: list[Ficha], csv_path: Path, json_path: Path | None = None
) -> Path:
    """Escribe el catalogo en CSV (Excel) y, si se pide, en JSON."""
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS, delimiter=";")
        escritor.writeheader()
        for ficha in fichas:
            fila = ficha.to_dict()
            fila["autores"] = ficha.autores_texto
            fila["reordenado"] = "si" if ficha.reordenado else "no"
            escritor.writerow({clave: fila.get(clave, "") for clave in COLUMNAS})

    if json_path is not None:
        json_path = Path(json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(
            json.dumps(
                {
                    "generado": datetime.now().isoformat(timespec="seconds"),
                    "total": len(fichas),
                    "fichas": [ficha.to_dict() for ficha in fichas],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return csv_path


