"""Perfil legal: expedientes judiciales (civil y laboral)."""

from .catalogo import CAMPOS, CATEGORIAS, CAT_OTROS, T_SIN_CLASIFICAR
from .catalogo import categoria_de_tipo, criticos_para_tipo, detalle_de, refinar, tipo_canonico
from .clasificacion import clasificar
from .extractores import extract_legal
from . import naturaleza

from ..base import Perfil


class PerfilLegal(Perfil):
    nombre = "legal"
    descripcion = (
        "Escritos, resoluciones, notificaciones y prueba de un expediente judicial."
    )

    categorias = CATEGORIAS
    campos = CAMPOS
    marcadores = (
        "demanda",
        "contestacion",
        "replica",
        "duplica",
        "recurso de apelacion",
        "sentencia definitiva",
        "auto de prueba",
        "proveido",
        "cedula de notificacion",
        "notificacion electronica",
        "contrato",
        "poder notarial",
        "mandato judicial",
        "informe pericial",
        "certificado",
        "boleta electronica",
        "factura electronica",
        "oficio",
        "pagare",
    )
    tipo_ficha = ""
    tipo_sin_clasificar = T_SIN_CLASIFICAR
    clave_fichas = ""
    titulo_informe = "INFORME DE DOCUMENTACION JUDICIAL"
    etiqueta_titular = "Parte"
    usa_titulares = False
    usa_prestadores = False

    def clasificar(self, texto: str):
        return clasificar(texto)

    def clasificar_naturaleza(self, texto: str):
        return naturaleza.clasificar(texto)

    def etiqueta_naturaleza(self, clave: str) -> str:
        return naturaleza.etiqueta(clave)

    def extractor(self, familia: str):
        return extract_legal

    def tipo_canonico(self, documento):
        return tipo_canonico(documento)

    def categoria_de_tipo(self, tipo: str) -> str:
        return categoria_de_tipo(tipo)

    def detalle_de(self, documento) -> str:
        return detalle_de(documento)

    def refinar(self, documento, prestadores: tuple | None = None) -> None:
        refinar(documento, prestadores=prestadores)

    def criticos_de(self, documento) -> tuple[str, ...]:
        """Campos criticos propios del tipo (un contrato no exige ROL)."""
        return criticos_para_tipo(self.tipo_canonico(documento))

    def identificadores(self, documento) -> dict[str, str]:
        valores = super().identificadores(documento)
        rol = str(documento.extra.get("rol").value or "").strip() if documento.extra.get("rol") else ""
        if rol:
            valores["rol"] = rol
        return valores

    def columnas(self) -> tuple[tuple[str, str], ...]:
        return (
            ("N", "N"),
            ("categoria", "Grupo"),
            ("naturaleza", "Fuente"),
            ("tipo", "Documento"),
            ("fecha", "Fecha"),
            ("rol", "ROL / RIT"),
            ("tribunal", "Tribunal"),
            ("caratula", "Caratula"),
            ("parte", "Parte"),
            ("folio", "Folio"),
            ("detalle", "Elementos de individualizacion"),
        )

    def etiqueta_familia(self, familia: str) -> str:
        from .clasificacion import FAMILY_LABELS

        return FAMILY_LABELS.get(familia, familia)
