"""Registro de perfiles disponibles."""

from __future__ import annotations

from functools import lru_cache

from .base import Perfil

PERFILES: tuple[str, ...] = ("salud", "legal")


@lru_cache(maxsize=None)
def get_perfil(nombre: str | None = None) -> Perfil:
    """Devuelve el perfil pedido (``salud`` por defecto)."""
    clave = (nombre or "salud").strip().lower()
    if clave in ("salud", "health", ""):
        from .salud import PerfilSalud

        return PerfilSalud()
    if clave in ("legal", "juridico", "jurídico"):
        from .legal import PerfilLegal

        return PerfilLegal()
    raise ValueError(
        f"Perfil desconocido: {nombre!r}. Disponibles: {', '.join(PERFILES)}"
    )
