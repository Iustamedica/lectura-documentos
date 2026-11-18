"""Extractor de la modalidad actos administrativos."""

from __future__ import annotations

from ...models import CONF_MEDIA, Document


def extract_administrativo(block, doc: Document) -> Document:
    if not doc.texto_ocr:
        doc.texto_ocr = block.text
    perfil = _perfil()
    perfil.refinar(doc)
    if not doc.titulo:
        doc.titulo = doc.tipo_documento.value or doc.source_file
    if not doc.tipo_documento.value:
        doc.tipo_documento.set(perfil.tipo_canonico(doc), CONF_MEDIA)
    return doc


def _perfil():
    from . import PerfilAdministrativo

    return PerfilAdministrativo()
