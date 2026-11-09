"""Perfil ``salud``: expediente de prestaciones medicas.

Delega en los modulos historicos para que el comportamiento sea **identico** al
que ya tenia la herramienta (es el perfil por defecto de la linea de comandos).
"""

from __future__ import annotations

from typing import Any, Callable

from .. import categorias as catalogo
from ..classify import FAMILY_LABELS, FARMACIA, classify
from ..extractors import get_extractor
from ..models import CRITICAL_FIELD_NAMES, Document
from ..normalizers import rut_body
from .base import CampoDef, Categoria, Perfil


class PerfilSalud(Perfil):
    nombre = "salud"
    descripcion = "Bonos, fichas, recetas, boletas y certificados de un expediente de salud."

    categorias = tuple(
        Categoria(clave=clave, etiqueta=etiqueta, carpeta=carpeta)
        for clave, etiqueta, carpeta in catalogo.CATEGORIAS
    )
    campos: tuple[CampoDef, ...] = ()
    marcadores: tuple[str, ...] = (
        "bono de atencion",
        "bono de atencion ambulatoria",
        "programa de atencion",
        "boleta electronica",
        "boleta de honorarios",
        "boleta electronica exenta",
        "receta optica",
        "solicitud de examenes",
        "pagare",
        "comprobante de venta",
        "informe medico",
        "certificado medico",
    )
    tipo_ficha = catalogo.T_FICHA
    tipo_sin_clasificar = catalogo.T_SIN_CLASIFICAR
    clave_fichas = catalogo.CAT_FICHAS
    titulo_informe = "INFORME DE DOCUMENTACION MEDICA"
    etiqueta_titular = "Titular"
    usa_titulares = True
    usa_prestadores = True

    # -- clasificacion --------------------------------------------------
    def clasificar(self, texto: str):
        return classify(texto)

    def ajustar_familia(self, familia: str, texto_plegado: str) -> str:
        """Reglas historicas del pipeline de salud."""
        # Una receta de farmacia no es una receta optica.
        if familia == FARMACIA and "receta" in texto_plegado and "farmacia" not in texto_plegado:
            familia = "receta_optica"
        # Voucher de tarjeta que acompana a una boleta: no es documento autonomo.
        if _es_voucher_de_pago(texto_plegado):
            familia = "comprobante_pago"
        # Receta manuscrita del oftalmologo: texto corto, "Rp." y datos del medico.
        if familia == "documento_clinico" and _parece_manuscrita(texto_plegado):
            familia = "receta_manuscrita"
        return familia

    def extractor(self, familia: str) -> Callable[..., Any]:
        return get_extractor(familia)

    # -- tipos y categorias --------------------------------------------
    def tipo_canonico(self, documento: Document) -> str:
        return catalogo.tipo_canonico(documento)

    def categoria_de_tipo(self, tipo: str) -> str:
        return catalogo.categoria_de_tipo(tipo)

    def tipo_de_grupo(self, documentos: list[Document]) -> str:
        return catalogo.tipo_de_grupo(documentos)

    def detalle_de(self, documento: Document) -> str:
        return catalogo.detalle_de(documento)

    def refinar(self, documento: Document, prestadores: tuple | None = None) -> None:
        catalogo.refinar(documento, prestadores=prestadores)

    # -- campos ---------------------------------------------------------
    def campos_criticos(self) -> tuple[str, ...]:
        return CRITICAL_FIELD_NAMES

    def etiquetas_campo(self) -> dict[str, str]:
        from ..report_docx import FIELD_LABELS

        return dict(FIELD_LABELS)

    def etiqueta_familia(self, familia: str) -> str:
        return FAMILY_LABELS.get(familia, familia)

    # -- individualizacion ---------------------------------------------
    def identificadores(self, documento: Document) -> dict[str, str]:
        valores = super().identificadores(documento)
        rut = rut_body(documento.titular_rut.value or None)
        if rut:
            valores["rut"] = str(rut)
        return valores

    def columnas(self) -> tuple[tuple[str, str], ...]:
        return (
            ("N", "N"),
            ("categoria", "Grupo"),
            ("tipo", "Documento"),
            ("fecha", "Fecha"),
            ("emisor", "Emisor / prestador"),
            ("titular", "Titular"),
            ("rut_titular", "RUT"),
            ("folio", "Folio"),
            ("monto_total", "Monto"),
            ("detalle", "Elementos de individualizacion"),
        )


def _es_voucher_de_pago(texto_plegado: str) -> bool:
    """True si el bloque es el comprobante de una transaccion con tarjeta."""
    marcadores = (
        "transbank",
        "klap",
        "tarjeta de debito",
        "tarjeta-de debito",
        "valido como boleta",
    )
    return sum(1 for marcador in marcadores if marcador in texto_plegado) >= 2


def _parece_manuscrita(texto_plegado: str) -> bool:
    """True si el bloque parece una receta escrita a mano por el oftalmologo."""
    if "rp." not in texto_plegado and "receta" not in texto_plegado:
        return False
    return "oftalmolog" in texto_plegado or "vision en familia" in texto_plegado
