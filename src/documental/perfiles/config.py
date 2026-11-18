"""Resolucion del perfil (modalidad) documental para la linea de comandos.

El repositorio publico trabaja por defecto en **judicial**. Los otros modos se
activan con ``--perfil``, con la variable ``DOCUMENTAL_PERFIL``, con un archivo
``perfil.txt`` en la carpeta de trabajo o, si no hay nada de eso, por el nombre
de la carpeta (``Doctrina``, ``Jurisprudencia``, ``Actos administrativos``...).
"""

from __future__ import annotations

import os
from pathlib import Path

from ..normalizers import fold
from .base import Perfil
from .registro import get_perfil

ARCHIVO_PERFIL = "perfil.txt"
PERFIL_POR_DEFECTO = "judicial"


def _carpeta_base(carpeta: Path | str | None) -> Path | None:
    if not carpeta:
        return None
    base = Path(carpeta)
    return base.parent if base.is_file() else base


def perfil_de_carpeta(carpeta: Path | str | None) -> str | None:
    """Perfil declarado en ``perfil.txt`` dentro de la carpeta de trabajo."""
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
    return None


def modalidad_de_carpeta(carpeta: Path | str | None) -> str | None:
    """Modalidad sugerida por el nombre de la carpeta (o de sus padres).

    Permite que una carpeta llamada ``Doctrina``, ``Jurisprudencia`` o
    ``Actos administrativos`` se procese sola, sin configurar nada.
    """
    base = _carpeta_base(carpeta)
    if base is None:
        return None
    candidatas = (base, base.parent, base.parent.parent)
    # Primero las modalidades especificas; judicial queda como respaldo.
    for clave in ("doctrina", "jurisprudencia", "administrativo", "judicial"):
        perfil = get_perfil(clave)
        pistas = perfil.pistas_carpeta
        if not pistas:
            continue
        for parte in candidatas:
            nombre = fold(parte.name)
            if any(pista in nombre for pista in pistas):
                return clave
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
    4. nombre de la carpeta (``Doctrina``, ``Jurisprudencia``...);
    5. perfil guardado en el expediente JSON;
    6. **judicial** (perfil publico por defecto).
    """
    nombre = (explicito or "").strip().lower()
    if not nombre:
        nombre = os.environ.get("DOCUMENTAL_PERFIL", "").strip().lower()
    if not nombre:
        nombre = perfil_de_carpeta(carpeta) or ""
    if not nombre:
        nombre = modalidad_de_carpeta(carpeta) or ""
    if not nombre and expediente is not None:
        nombre = str(getattr(expediente, "perfil", "") or "").strip().lower()
    return get_perfil(nombre or PERFIL_POR_DEFECTO)
