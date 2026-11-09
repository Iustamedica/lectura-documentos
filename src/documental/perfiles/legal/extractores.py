"""Extractor del perfil legal.

El pipeline ya hizo el OCR y guardo el texto en ``Document.texto_ocr``; aqui se
leen el ROL, el tribunal, las partes y los demas datos del expediente.
"""

from __future__ import annotations

from ...models import Document
from . import catalogo


def extract_legal(block, doc: Document) -> Document:
    """Completa los datos legales del documento a partir de su texto."""
    if not doc.texto_ocr:
        doc.texto_ocr = block.text
    catalogo.refinar(doc)
    if not doc.titulo:
        doc.titulo = catalogo.tipo_canonico(doc)
    return doc
