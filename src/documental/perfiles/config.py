"""Resolucion del perfil documental para la linea de comandos.

El repositorio publico trabaja por defecto en **legal**. El modo **salud** se
activa con ``--perfil salud``, con la variable ``DOCUMENTAL_PERFIL`` o con un
archivo ``perfil.txt`` en la carpeta de trabajo.

Para no romper las carpetas de salud que ya existen, si la carpeta contiene un
``caso.json`` (ficha de titulares del flujo de salud) se asume el perfil salud.
"""

from __future__ import annotations

import os
from pathlib import Path

from .base import Perfil
from .registro import get_perfil

ARCHIVO_PERFIL = "perfil.txt"
PERFIL_POR_DEFECTO = "legal"


def _carpeta_base(carpeta: Path | str | None) -> Path | None:
    if not carpeta:
        return None
    base = Path(carpeta)
    return base.parent if base.is_file() else base


def perfil_de_carpeta(carpeta: Path | str | None) -> str | None:
    """Perfil declarado en la carpeta de trabajo (``perfil.txt`` o ``caso.json``)."""
    base = _carpeta_base(carpeta)
    if base is None:
        return None
    archivo = base / ARCHIVO_PERFIL
    if archivo.is_file():
        try:
            nombre = archivo.read_text(encoding="utf-8").strip().lower()
        except OSError:
            nombre = ""
        if nombre:
            return nombre
    if (base / "caso.json").is_file():
        return "salud"
    return None


def resolver_perfil(
    explicito: str | None = None,
    carpeta: Path | str | None = None,
    expediente=None,
) -> Perfil:
    """Devuelve el perfil a usar, en orden de prioridad.

    1. ``--perfil`` explicito;
    2. variable de entorno ``DOCUMENTAL_PERFIL``;
    3. ``perfil.txt`` en la carpeta de trabajo;
    4. ``caso.json`` en la carpeta (compatibilidad con el flujo de salud);
    5. perfil guardado en el expediente JSON;
    6. **legal** (perfil publico por defecto).
    """
    nombre = (explicito or "").strip().lower()
    if not nombre:
        nombre = os.environ.get("DOCUMENTAL_PERFIL", "").strip().lower()
    if not nombre:
        nombre = perfil_de_carpeta(carpeta) or ""
    if not nombre and expediente is not None:
        nombre = str(getattr(expediente, "perfil", "") or "").strip().lower()
    return get_perfil(nombre or PERFIL_POR_DEFECTO)
