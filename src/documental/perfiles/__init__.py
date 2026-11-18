"""Perfiles (modalidades) documentales.

Un perfil describe *que* documentos conoce el sistema y *como* se individualizan.
El motor (OCR, layout, revisor, compilador) es comun a todas las modalidades.

Modalidades disponibles:

    judicial          escritos, resoluciones, contratos, boletas y prueba
    doctrina          libros, articulos, tesis y papers (un PDF = un item)
    jurisprudencia    sentencias de la Corte Suprema, Cortes y TC
    administrativo    resoluciones, dictamenes y oficios de organos publicos
"""

from .base import CampoDef, Categoria, Perfil
from .config import modalidad_de_carpeta, resolver_perfil
from .registro import PERFILES, get_perfil

__all__ = [
    "PERFILES",
    "CampoDef",
    "Categoria",
    "Perfil",
    "get_perfil",
    "modalidad_de_carpeta",
    "resolver_perfil",
]
