"""Clasificacion rapida SIN OCR, usando la capa de texto de los PDF.

Sirve para inventariar y clasificar grandes carpetas en segundos: los PDF que ya
traen texto (resoluciones, escritos, boletas digitales, etc.) se clasifican con su
texto; los escaneos e imagenes se marcan como "requiere OCR" (no se procesan).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf

from .categorias import categoria_de_tipo, tipo_canonico
from .classify import DESCONOCIDO, classify
from .models import Document

_SUF_PDF = {".pdf"}
_SUF_IMG = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
_MIN_CARACTERES = 40


@dataclass
class ItemClasificado:
    archivo: str
    paginas: int
    tiene_texto: bool
    familia: str
    tipo: str
    categoria: str


def _texto_pdf(path: Path, max_paginas: int = 5) -> tuple[int, str]:
    with pymupdf.open(str(path)) as pdf:
        total = pdf.page_count
        partes = [pdf[i].get_text("text") for i in range(min(total, max_paginas))]
    return total, "".join(partes)


def clasificar_sin_ocr(
    carpeta: Path | str,
    recursivo: bool = True,
    max_paginas: int = 5,
    perfil=None,
) -> list[ItemClasificado]:
    """Clasifica cada archivo usando solo su texto embebido (sin OCR)."""
    if perfil is None:
        from .perfiles import get_perfil

        perfil = get_perfil()
    carpeta = Path(carpeta)
    if carpeta.is_file():
        archivos = [carpeta]
        base = carpeta.parent
    else:
        candidatos = carpeta.rglob("*") if recursivo else carpeta.iterdir()
        archivos = sorted(p for p in candidatos if p.is_file())
        base = carpeta

    items: list[ItemClasificado] = []
    for p in archivos:
        suf = p.suffix.lower()
        rel = str(p.relative_to(base))
        if suf in _SUF_PDF:
            try:
                paginas, texto = _texto_pdf(p, max_paginas=max_paginas)
            except Exception:
                items.append(ItemClasificado(rel, 0, False, DESCONOCIDO,
                                             "(ilegible)", "otros"))
                continue
            if len(texto.strip()) >= _MIN_CARACTERES:
                familia = perfil.clasificar(texto).familia
                doc = Document(
                    doc_id=p.name, source_file=p.name, page=1, index_in_page=1,
                    familia=familia, texto_ocr=texto,
                )
                tipo = perfil.tipo_canonico(doc)
                items.append(ItemClasificado(rel, paginas, True, familia, tipo,
                                             perfil.categoria_de_tipo(tipo)))
            else:
                items.append(ItemClasificado(rel, paginas, False, DESCONOCIDO,
                                             "(escaneo: requiere OCR)", "otros"))
        elif suf in _SUF_IMG:
            items.append(ItemClasificado(rel, 1, False, DESCONOCIDO,
                                         "(imagen: requiere OCR)", "otros"))
    return items


def resumen(items: list[ItemClasificado]) -> dict:
    """Cuenta documentos por categoria y por tipo (solo los que tienen texto)."""
    con_texto = [i for i in items if i.tiene_texto]
    por_categoria: dict[str, int] = {}
    por_tipo: dict[str, int] = {}
    for i in con_texto:
        por_categoria[i.categoria] = por_categoria.get(i.categoria, 0) + 1
        por_tipo[i.tipo] = por_tipo.get(i.tipo, 0) + 1
    return {
        "total": len(items),
        "con_texto": len(con_texto),
        "requiere_ocr": len(items) - len(con_texto),
        "por_categoria": dict(sorted(por_categoria.items(), key=lambda x: -x[1])),
        "por_tipo": dict(sorted(por_tipo.items(), key=lambda x: -x[1])),
    }


def escribir_csv(items: list[ItemClasificado], destino: Path) -> Path:
    import csv

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(["archivo", "paginas", "tiene_texto", "familia", "tipo", "categoria"])
        for i in items:
            w.writerow([i.archivo, i.paginas, i.tiene_texto, i.familia, i.tipo, i.categoria])
    return destino
