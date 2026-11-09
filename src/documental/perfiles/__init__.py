"""Perfiles documentales: que categorias, campos y extractores usa el motor.

Un perfil describe *que* documentos conoce el sistema y *como* se individualizan.
El motor (OCR, layout, revisor, compilador) es comun a todos los perfiles.

Perfiles disponibles:

    salud   bonos, fichas, recetas y boletas de un expediente de salud (por defecto)
    legal   escritos, resoluciones y prueba de un expediente judicial
"""

from .base import CampoDef, Categoria, Perfil
from .registro import PERFILES, get_perfil

__all__ = ["PERFILES", "CampoDef", "Categoria", "Perfil", "get_perfil"]
