"""Registro de perfiles disponibles."""

from __future__ import annotations

from functools import lru_cache

from .base import Perfil

PERFILES: tuple[str, ...] = (
    "judicial",
    "doctrina",
    "jurisprudencia",
    "administrativo",
)

# Alias aceptados en ``--perfil`` y en ``perfil.txt``.
ALIASES: dict[str, str] = {
    "legal": "judicial",
    "judicial": "judicial",
    "expediente": "judicial",
    # Compatibilidad: configuraciones antiguas de salud caen en judicial.
    "salud": "judicial",
    "health": "judicial",
    "doctrina": "doctrina",
    "biblioteca": "doctrina",
    "libros": "doctrina",
    "jurisprudencia": "jurisprudencia",
    "sentencias": "jurisprudencia",
    "administrativo": "administrativo",
    "actos": "administrativo",
    "contencioso": "administrativo",
}


@lru_cache(maxsize=None)
def get_perfil(nombre: str | None = None) -> Perfil:
    """Devuelve el perfil pedido (``judicial`` por defecto)."""
    clave = (nombre or "judicial").strip().lower()
    clave = ALIASES.get(clave, clave)
    if clave == "judicial":
        from .legal import PerfilLegal

        return PerfilLegal()
    if clave == "doctrina":
        from .doctrina import PerfilDoctrina

        return PerfilDoctrina()
    if clave == "jurisprudencia":
        from .jurisprudencia import PerfilJurisprudencia

        return PerfilJurisprudencia()
    if clave == "administrativo":
        from .administrativo import PerfilAdministrativo

        return PerfilAdministrativo()
    raise ValueError(
        f"Perfil desconocido: {nombre!r}. Disponibles: {', '.join(PERFILES)}"
    )
