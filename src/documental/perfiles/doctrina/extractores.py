"""Extractor de la modalidad doctrina.

La ficha bibliografica se completa al construir el documento completo (ver
``PerfilDoctrina.enriquecer_completo``); aqui solo se asegura el tipo canonico.
"""

from __future__ import annotations

from ...models import CONF_MEDIA, Document


def extract_doctrina(block, doc: Document) -> Document:
    if not doc.texto_ocr:
        doc.texto_ocr = block.text
    if not doc.titulo:
        doc.titulo = doc.source_file
    doc.tipo_documento.set(doc.tipo_documento.value or "Publicacion de doctrina", CONF_MEDIA)
    return doc
