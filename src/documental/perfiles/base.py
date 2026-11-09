"""Contrato comun de un perfil documental.

El motor llama solo a estos metodos; cada perfil decide el catalogo, la
clasificacion, los extractores y la forma de individualizar. El perfil ``salud``
delega en los modulos historicos (``categorias``, ``classify``, ``extractors``)
para no cambiar el comportamiento existente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..models import Document


@dataclass(frozen=True)
class Categoria:
    """Una carpeta de salida (``clave`` es el identificador interno)."""

    clave: str
    etiqueta: str
    carpeta: str


@dataclass(frozen=True)
class CampoDef:
    """Campo extraible, con su etiqueta y si es critico para el semaforo."""

    nombre: str
    etiqueta: str
    critico: bool = False


class Perfil:
    """Catalogo y reglas de un dominio documental."""

    nombre: str = ""
    descripcion: str = ""

    categorias: tuple[Categoria, ...] = ()
    # Campos propios del perfil (ademas de los campos comunes del modelo).
    campos: tuple[CampoDef, ...] = ()
    # Marcadores que inician un documento nuevo dentro de una hoja.
    marcadores: tuple[str, ...] = ()
    # Tipo generico y tipo "sin clasificar" del perfil (para consolidar hojas).
    tipo_ficha: str = ""
    tipo_sin_clasificar: str = "Documento sin clasificar"
    # Clave de la categoria que agrupa las fichas por emisor (solo salud).
    clave_fichas: str = ""
    # Textos del informe.
    titulo_informe: str = "INFORME DE DOCUMENTACION"
    etiqueta_titular: str = "Titular"
    usa_titulares: bool = True
    usa_prestadores: bool = False

    # ------------------------------------------------------------------
    # Catalogo
    # ------------------------------------------------------------------
    @property
    def clave_otros(self) -> str:
        """Clave de la categoria "otros" (la ultima del catalogo)."""
        return self.categorias[-1].clave if self.categorias else "otros"

    def categoria(self, clave: str) -> Categoria:
        for item in self.categorias:
            if item.clave == clave:
                return item
        return Categoria(clave, clave, clave)

    def etiqueta(self, clave: str) -> str:
        return self.categoria(clave).etiqueta

    def carpeta(self, clave: str) -> str:
        return self.categoria(clave).carpeta

    def etiquetas_categoria(self) -> dict[str, str]:
        return {item.clave: item.etiqueta for item in self.categorias}

    def campos_criticos(self) -> tuple[str, ...]:
        return tuple(item.nombre for item in self.campos if item.critico)

    def etiquetas_campo(self) -> dict[str, str]:
        return {item.nombre: item.etiqueta for item in self.campos}

    def definicion_campo(self, nombre: str) -> CampoDef | None:
        for item in self.campos:
            if item.nombre == nombre:
                return item
        return None

    def columnas(self) -> tuple[tuple[str, str], ...]:
        """Columnas de la tabla de individualizacion (clave, etiqueta)."""
        return (
            ("N", "N"),
            ("categoria", "Grupo"),
            ("tipo", "Documento"),
            ("fecha", "Fecha"),
            ("emisor", "Emisor"),
            ("titular", self.etiqueta_titular),
            ("folio", "Folio"),
            ("detalle", "Elementos de individualizacion"),
        )

    # ------------------------------------------------------------------
    # Hooks que implementa cada perfil
    # ------------------------------------------------------------------
    def clasificar(self, texto: str):
        """Devuelve una ``Classification`` (familia, confianza, puntajes)."""
        raise NotImplementedError

    def ajustar_familia(self, familia: str, texto_plegado: str) -> str:
        """Corrige la familia con reglas propias del perfil."""
        return familia

    def extractor(self, familia: str) -> Callable[..., Any]:
        """Extractor de la familia detectada."""
        raise NotImplementedError

    def tipo_canonico(self, documento: Document) -> str:
        """Nombre canonico del instrumento (lo que cita el escrito)."""
        raise NotImplementedError

    def categoria_de_tipo(self, tipo: str) -> str:
        """Categoria (carpeta) a la que pertenece un tipo canonico."""
        raise NotImplementedError

    def tipo_de_grupo(self, documentos: list[Document]) -> str:
        """Tipo canonico que representa un documento de varias hojas."""
        tipos = [self.tipo_canonico(item) for item in documentos]
        utiles = [tipo for tipo in tipos if tipo != self.tipo_sin_clasificar]
        if not utiles:
            return self.tipo_sin_clasificar
        concretos = [tipo for tipo in utiles if tipo != self.tipo_ficha]
        candidatos = concretos or utiles
        conteo: dict[str, int] = {}
        for tipo in candidatos:
            conteo[tipo] = conteo.get(tipo, 0) + 1
        return max(conteo, key=lambda clave: (conteo[clave], -candidatos.index(clave)))

    def detalle_de(self, documento: Document) -> str:
        """Elementos que el escrito necesita y no tienen columna propia."""
        return ""

    def etiqueta_familia(self, familia: str) -> str:
        """Nombre legible de la familia detectada por el clasificador."""
        return familia

    def refinar(self, documento: Document, prestadores: tuple | None = None) -> None:
        """Completa los datos que falten leyendolos del texto OCR ya guardado."""
        return None

    # ------------------------------------------------------------------
    # Individualizacion
    # ------------------------------------------------------------------
    def identificadores(self, documento: Document) -> dict[str, str]:
        """Valores que identifican fisicamente un documento.

        Dos bloques con identificadores distintos son documentos diferentes
        (dos bonos en la misma hoja, dos expedientes en el mismo PDF).
        """
        return {"folio": str(documento.folio.value or "").strip()}

    def conflicto(self, anteriores: list[Document], posteriores: list[Document]) -> bool:
        """True si los bloques no pueden ser partes del mismo documento."""
        ids_a: dict[str, set[str]] = {}
        ids_b: dict[str, set[str]] = {}
        for documento in anteriores:
            for clave, valor in self.identificadores(documento).items():
                if valor:
                    ids_a.setdefault(clave, set()).add(valor)
        for documento in posteriores:
            for clave, valor in self.identificadores(documento).items():
                if valor:
                    ids_b.setdefault(clave, set()).add(valor)
        for clave in ids_a.keys() & ids_b.keys():
            if not (ids_a[clave] & ids_b[clave]):
                return True
        return False
