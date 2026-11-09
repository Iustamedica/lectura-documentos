"""Revisor HTML autocontenido para corregir los datos extraidos.

Se abre con doble clic en cualquier navegador (no requiere servidor ni
internet). Permite ver cada documento con su recorte, corregir cualquier valor
y exportar el JSON corregido, que luego se usa para regenerar el Word.

El estado se guarda ademas en el `localStorage` del navegador para no perder
trabajo si se cierra la pestana por error.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import CRITICAL_FIELD_NAMES, Expediente
from .report_docx import AMOUNT_FIELDS, FIELD_LABELS

# Campos editables en el revisor (todos los que aparecen en el informe).
EDITABLE_FIELDS = tuple(FIELD_LABELS.keys())

_TEMPLATE_PATH = Path(__file__).with_name("revisor_template.html")


def generar_revisor(
    expediente: Expediente,
    destino: Path,
    *,
    image_rel_prefix: str = "render/",
    perfil=None,
) -> Path:
    """Genera el HTML de revision y devuelve su ruta.

    `image_rel_prefix` es la ruta relativa desde el HTML hasta la carpeta de
    recortes generada por el pipeline (por defecto `salidas/render/`).
    """
    if perfil is None:
        from .perfiles import get_perfil

        perfil = get_perfil()
    etiquetas = dict(FIELD_LABELS)
    etiquetas.update(perfil.etiquetas_campo())
    editable = tuple(etiquetas.keys())
    criticos = tuple(perfil.campos_criticos())

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    payload = expediente.to_dict()
    # Semaforo por documento en la cabecera de cada tarjeta.
    for doc_dict, doc in zip(payload["documentos"], expediente.documentos):
        doc_dict["confianza"] = doc.confianza_global(criticos)
        # Los campos del perfil se exponen planos para que el revisor los
        # muestre y los exporte igual que los campos comunes.
        for nombre, campo in (doc_dict.get("extra") or {}).items():
            doc_dict.setdefault(nombre, campo)
    payload["prefijo_imagenes"] = image_rel_prefix

    plantilla = _TEMPLATE_PATH.read_text(encoding="utf-8")
    datos = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = (
        plantilla.replace("__TITULO__", Path(expediente.carpeta).name)
        .replace("__DATOS__", datos)
        .replace("__ETIQUETAS__", json.dumps(etiquetas, ensure_ascii=False))
        .replace("__CRITICOS__", json.dumps(list(criticos), ensure_ascii=False))
        .replace("__CAMPOS__", json.dumps(list(editable), ensure_ascii=False))
        .replace("__MONTO__", json.dumps(sorted(AMOUNT_FIELDS), ensure_ascii=False))
    )
    destino.write_text(html, encoding="utf-8")
    return destino


def cargar_expediente(path: Path) -> Expediente:
    """Carga un expediente desde JSON (base o corregido en el revisor)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Expediente.from_dict(data)


def aplicar_correcciones(expediente: Expediente, base: dict) -> int:
    """Aplica correcciones de un dict (JSON corregido) sobre el expediente.

    Se usa cuando el abogado prefiere corregir directamente el JSON en un editor
    (VS Code) en lugar del revisor HTML. Devuelve cuantos campos cambiaron.

    Reglas:
      - Un campo con `edited: true` en el JSON corregido reemplaza el valor.
      - Un campo con valor distinto al original tambien se reemplaza (por si el
        revisor exporto sin marcar `edited`) y se marca como corregido.
    """
    original = expediente.to_dict()
    cambios = 0
    por_id = {d["doc_id"]: d for d in base.get("documentos", [])}
    for doc_dict in original["documentos"]:
        for nombre, campo in (doc_dict.get("extra") or {}).items():
            doc_dict.setdefault(nombre, campo)
        corregido = por_id.get(doc_dict["doc_id"])
        if not corregido:
            continue
        for nombre, campo in doc_dict.items():
            nuevo = corregido.get(nombre)
            if not isinstance(campo, dict) or not isinstance(nuevo, dict):
                continue
            if nuevo.get("value") != campo.get("value") or nuevo.get("edited"):
                if nuevo.get("value") != campo.get("value"):
                    cambios += 1
                campo["value"] = nuevo.get("value")
                campo["confidence"] = nuevo.get("confidence", "alta")
                campo["edited"] = True
    actualizado = Expediente.from_dict(original)
    expediente.documentos = actualizado.documentos
    return cambios
