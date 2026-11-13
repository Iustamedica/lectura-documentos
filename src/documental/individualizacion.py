"""Individualizacion de los documentos de un expediente.

Para presentar documentos ante un tribunal hay que poder decir "Documento N 3:
bono de atencion FONASA de fecha 12-03-2026, otorgado por ..., a nombre de
...". Este modulo agrupa las paginas que pertenecen a un mismo documento fisico
(un contrato o un informe de varias hojas) y los numera en orden cronologico,
de modo que el numero del escrito coincida con el del PDF compilado.

La agrupacion es deliberadamente conservadora: solo une paginas consecutivas
del mismo archivo, de la misma familia y con el mismo folio y titular. Ante la
duda deja documentos separados, porque en un expediente judicial es preferible
un documento de mas que uno mal unido.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from docx import Document as DocxDocument
from docx.shared import Pt

from .categorias import (
    CAT_OTROS,
    CATEGORIA_ETIQUETA,
    T_FICHA,
    T_SIN_CLASIFICAR,
    categoria_de,
    categoria_de_tipo,
    detalle_de,
    tipo_canonico,
    tipo_de_grupo,
)
from .models import CONFIDENCE_ORDER, Document
from .normalizers import format_clp, format_date_cl, parse_date, rut_body
from .perfiles import Perfil, get_perfil

# Campos que se prueban, en este orden, para fechar un documento.
CAMPOS_FECHA = ("fecha_emision", "fecha_atencion", "fecha_vencimiento")

# Columnas de la tabla de individualizacion (orden del escrito).
COLUMNAS = (
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


def _texto(campo) -> str:
    """Valor de un ``Field`` como texto limpio (vacio si no hay dato)."""
    valor = getattr(campo, "value", campo)
    if valor in (None, "", [], {}):
        return ""
    return str(valor).strip()


def fecha_de(documento: Document) -> date | None:
    """Fecha del documento, probando emision, atencion y vencimiento."""
    for nombre in CAMPOS_FECHA:
        valor = documento.field(nombre).value
        if isinstance(valor, datetime):
            return valor.date()
        if isinstance(valor, date):
            return valor
        encontrada = parse_date(str(valor)) if valor else None
        if encontrada:
            return encontrada
    return None


def _rut_de(documento: Document) -> int | None:
    return rut_body(documento.titular_rut.value or None)


def _compatible(tipo_a: str, tipo_b: str, perfil: Perfil) -> bool:
    """True si dos bloques pueden ser partes del mismo documento fisico."""
    if tipo_a == tipo_b:
        return True
    genericos = {perfil.tipo_ficha, perfil.tipo_sin_clasificar}
    genericos.discard("")
    return tipo_a in genericos or tipo_b in genericos


def _sin_conflicto(
    anteriores: list[Document], posteriores: list[Document], perfil: Perfil
) -> bool:
    """True si los bloques no se contradicen en folio, RUT o ROL."""
    return not perfil.conflicto(anteriores, posteriores)


def _unidades_de_hoja(
    bloques: list[Document], perfil: Perfil | None = None
) -> list[list[Document]]:
    """Consolida los bloques de una misma hoja en documentos fisicos.

    El layout parte una hoja en varios bloques (columnas, tablas, un pie de
    pagina suelto), pero en una ficha clinica esos bloques son partes del mismo
    documento y no documentos distintos. En cambio, dos bonos en la misma hoja
    si son dos documentos: se distinguen porque tienen folios distintos.

    Los bloques que no se pudieron clasificar se adhieren a la categoria
    dominante de la hoja, porque un fragmento sin texto utilizable no constituye
    un documento autonomo.
    """
    perfil = perfil or get_perfil()
    tipos = [perfil.tipo_canonico(d) for d in bloques]
    categorias = [perfil.categoria_de_tipo(tipo) for tipo in tipos]
    dominante = next((c for c in categorias if c != perfil.clave_otros), "")
    asignadas = [
        dominante
        if (
            categoria == perfil.clave_otros
            and tipo == perfil.tipo_sin_clasificar
            and dominante
        )
        else categoria
        for categoria, tipo in zip(categorias, tipos)
    ]

    unidades: list[tuple[str, list[Document]]] = []
    for bloque, categoria in zip(bloques, asignadas):
        if (
            unidades
            and unidades[-1][0] == categoria
            and not perfil.conflicto(unidades[-1][1], [bloque])
        ):
            unidades[-1][1].append(bloque)
        else:
            unidades.append((categoria, [bloque]))
    return [documentos for _, documentos in unidades]


def _fusionar_bloques(bloques: list[Document]) -> Document:
    """Fusiona varios bloques (de la misma hoja y sin conflicto) en un Document.

    Conserva el primer bloque y completa sus campos vacios con los del resto, y
    concatena el texto OCR (para no perder datos al revisar).
    """
    base = bloques[0]
    for otro in bloques[1:]:
        base.texto_ocr = ((base.texto_ocr or "") + "\n" + (otro.texto_ocr or "")).strip()
        for nombre, campo in base.fields().items():
            try:
                otro_campo = otro.field(nombre)
            except (KeyError, AttributeError):
                continue
            if campo.is_empty and not otro_campo.is_empty:
                campo.value = otro_campo.value
                campo.confidence = otro_campo.confidence
                campo.raw = otro_campo.raw
                campo.note = otro_campo.note
        base.items.extend(otro.items)
        for nombre, campo in otro.extra.items():
            actual = base.extra.get(nombre)
            if actual is None:
                base.extra[nombre] = campo
            elif actual.is_empty and not campo.is_empty:
                base.extra[nombre] = campo
    return base


def _unidades_de_pagina(bloques: list[Document]) -> list[Document]:
    """Un documento por hoja, salvo que haya dos folios distintos (dos bonos).

    Regla pensada para el flujo ``expediente``: una hoja del escaneo normalmente
    es UN documento, aunque el layout la haya partido en varios bloques (y aun
    cuando un bloque quedo mal clasificado, p. ej. un falso "PAGARE"). Solo se
    separa cuando hay evidencia de dos documentos: folios diferentes.
    """
    por_folio: dict[str, list[Document]] = {}
    for bloque in bloques:
        folio = str(bloque.folio.value or "").strip()
        if folio:
            por_folio.setdefault(folio, []).append(bloque)
    if len(por_folio) >= 2:
        sin_folio = [
            b for b in bloques if not str(b.folio.value or "").strip()
        ]
        unidades = list(por_folio.values())
        if sin_folio:
            unidades[0].extend(sin_folio)
        return [_fusionar_bloques(u) for u in unidades]
    return [_fusionar_bloques(bloques)]


def consolidar_documentos(
    documentos: list[Document], perfil: Perfil | None = None
) -> list[Document]:
    """Une los bloques que pertenecen al mismo documento fisico de una hoja.

    El layout parte una hoja en varios bloques; aqui se agrupan por hoja y se
    fusionan en un solo ``Document`` (salvo que la hoja tenga dos folios
    distintos, que son dos documentos). Asi el revisor y el informe muestran un
    documento por hoja, sin fragmentos vacios ni falsos "PAGARE" sueltos.
    """
    por_hoja: dict[tuple, list[Document]] = {}
    for documento in documentos:
        por_hoja.setdefault((documento.source_file, documento.page), []).append(documento)
    resultado: list[Document] = []
    for bloques in por_hoja.values():
        resultado.extend(_unidades_de_pagina(bloques))
    return resultado


def _continua(
    anteriores: list[Document], posteriores: list[Document], perfil: Perfil
) -> bool:
    """True si ``posteriores`` es la hoja siguiente del mismo documento."""
    ultimo = anteriores[-1]
    primero = posteriores[0]
    if ultimo.source_file != primero.source_file:
        return False
    if primero.page != ultimo.page + 1 or primero.index_in_page != 1:
        return False

    categoria = perfil.categoria_de_tipo(perfil.tipo_canonico(ultimo))
    if categoria != perfil.categoria_de_tipo(perfil.tipo_canonico(primero)):
        return False
    if not _compatible(perfil.tipo_canonico(ultimo), perfil.tipo_canonico(primero), perfil):
        return False
    if perfil.conflicto(anteriores, posteriores):
        return False

    # Un documento sin clasificar puede ser cualquier cosa: solo se une con una
    # senal explicita (mismo folio o mismo RUT) que lo justifique.
    if (
        perfil.tipo_canonico(ultimo) == perfil.tipo_sin_clasificar
        and perfil.tipo_canonico(primero) == perfil.tipo_sin_clasificar
    ):
        claves = [perfil.identificadores(d) for d in anteriores + posteriores]
        for nombre in set().union(*(clave.keys() for clave in claves)):
            valores = {clave[nombre] for clave in claves if clave.get(nombre)}
            if len(valores) == 1:
                return True
        return False
    return True


@dataclass
class Grupo:
    """Un documento fisico: una o mas paginas que se presentan como una unidad."""

    numero: int
    documentos: list[Document] = field(default_factory=list)
    perfil: Perfil | None = None

    @property
    def _perfil(self) -> Perfil:
        return self.perfil or get_perfil()

    @property
    def primero(self) -> Document:
        return self.documentos[0]

    @property
    def archivo(self) -> str:
        return self.primero.source_file

    @property
    def paginas(self) -> list[int]:
        numeros: set[int] = set()
        for documento in self.documentos:
            numeros.update(documento.paginas or [documento.page])
        return sorted(numeros)

    @property
    def paginas_texto(self) -> str:
        paginas = self.paginas
        if not paginas:
            return ""
        if len(paginas) == 1:
            return f"p. {paginas[0]}"
        return f"pp. {paginas[0]}-{paginas[-1]}"

    @property
    def etiqueta(self) -> str:
        """Identificador corto usado en el PDF y en el escrito: ``DOC-03``."""
        return f"DOC-{self.numero:02d}"

    def valor(self, nombre: str) -> str:
        """Primer valor no vacio del campo entre los documentos del grupo."""
        for documento in self.documentos:
            texto = _texto(documento.field(nombre))
            if texto:
                return texto
        return ""

    @property
    def tipo(self) -> str:
        """Nombre del documento: el tipo canonico del grupo.

        Se calcula sobre todas las hojas del grupo para que un fragmento suelto
        en la primera hoja no bautice el documento completo.
        """
        return self._perfil.tipo_de_grupo(self.documentos)

    @property
    def categoria(self) -> str:
        """Categoria (bonos, boletas, fichas, recetas, certificados, otros).

        Se deriva del tipo del grupo y no del primer bloque: una hoja cuyo
        encabezado el OCR no pudo leer no debe arrastrar el documento entero a
        la carpeta de "otros".
        """
        return self._perfil.categoria_de_tipo(self._perfil.tipo_de_grupo(self.documentos))

    @property
    def naturaleza(self) -> str:
        """Naturaleza de la fuente, con su etiqueta legible."""
        return self._perfil.etiqueta_naturaleza(self.primero.naturaleza)

    @property
    def detalle(self) -> str:
        """Elementos propios de la categoria (prestador, detalle de compra...)."""
        for documento in self.documentos:
            texto = self._perfil.detalle_de(documento)
            if texto:
                return texto
        return ""

    @property
    def fecha(self) -> date | None:
        for documento in self.documentos:
            encontrada = fecha_de(documento)
            if encontrada:
                return encontrada
        return None

    @property
    def fecha_texto(self) -> str:
        return format_date_cl(self.fecha)

    @property
    def confianza(self) -> str:
        """Peor confianza entre las paginas del grupo."""
        criticos = self._perfil.criticos_de(self.primero)
        peor = self.primero.confianza_global(criticos)
        for documento in self.documentos[1:]:
            otra = documento.confianza_global(criticos)
            if CONFIDENCE_ORDER.get(otra, 9) > CONFIDENCE_ORDER.get(peor, 9):
                peor = otra
        return peor


def _clave_cronologica(bloque: list[Document]) -> tuple:
    """Ordena por fecha y, a igualdad, por el orden de los archivos."""
    fecha = None
    for documento in bloque:
        fecha = fecha_de(documento)
        if fecha:
            break
    primero = bloque[0]
    return (fecha is None, fecha or date.max, primero.source_file, primero.page)


def agrupar(documentos: list[Document], perfil: Perfil | None = None) -> list[Grupo]:
    """Agrupa y numera los documentos en orden cronologico.

    El proceso va de lo chico a lo grande: primero se consolidan los bloques de
    una misma hoja (que el layout puede haber partido en columnas o haber
    dejado con un pie de pagina suelto) y despues se unen las hojas
    consecutivas que pertenecen al mismo documento.
    """
    perfil = perfil or get_perfil()
    ordenados = sorted(
        documentos, key=lambda d: (d.source_file, d.page, d.index_in_page)
    )

    hojas: dict[tuple[str, int], list[Document]] = {}
    for documento in ordenados:
        hojas.setdefault((documento.source_file, documento.page), []).append(documento)

    unidades: list[list[Document]] = []
    for clave in hojas:  # el dict conserva el orden de insercion
        unidades.extend(_unidades_de_hoja(hojas[clave], perfil))

    bloques: list[list[Document]] = []
    for unidad in unidades:
        if bloques and _continua(bloques[-1], unidad, perfil):
            bloques[-1].extend(unidad)
        else:
            bloques.append(list(unidad))

    bloques = [bloque for bloque in bloques if bloque]
    bloques.sort(key=_clave_cronologica)
    return [
        Grupo(numero=numero, documentos=bloque, perfil=perfil)
        for numero, bloque in enumerate(bloques, start=1)
    ]


def filas(grupos: list[Grupo]) -> list[dict[str, str]]:
    """Una fila por documento, con lo que el escrito necesita individualizar."""
    resultado: list[dict[str, str]] = []
    for grupo in grupos:
        monto = grupo.valor("monto_total")
        resultado.append(
            {
                "N": str(grupo.numero),
                "categoria": grupo._perfil.etiqueta(grupo.categoria),
                "naturaleza": grupo.naturaleza,
                "tipo": grupo.tipo,
                "fecha": grupo.fecha_texto,
                "emisor": grupo.valor("emisor_nombre"),
                "rut_emisor": grupo.valor("emisor_rut"),
                "titular": grupo.valor("titular_nombre"),
                "rut_titular": grupo.valor("titular_rut"),
                "folio": grupo.valor("folio"),
                "rol": grupo.valor("rol"),
                "tribunal": grupo.valor("tribunal"),
                "caratula": grupo.valor("caratula"),
                "parte": grupo.valor("parte_demandante"),
                "parte_demandante": grupo.valor("parte_demandante"),
                "parte_demandada": grupo.valor("parte_demandada"),
                "monto_total": format_clp(int(monto)) if monto.isdigit() else monto,
                "detalle": grupo.detalle,
                "archivo": grupo.archivo,
                "pagina": grupo.paginas_texto,
                "confianza": grupo.confianza,
                "etiqueta": grupo.etiqueta,
            }
        )
    return resultado


def escribir_csv(grupos: list[Grupo], path: Path, perfil: Perfil | None = None) -> Path:
    """Escribe la tabla de individualizacion en CSV.

    Separador ``;`` y BOM de UTF-8 para que Excel en espanol lo abra en columnas
    sin pasos adicionales.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    perfil = perfil or (grupos[0]._perfil if grupos else get_perfil())
    columnas = [clave for clave, _ in perfil.columnas()] + ["archivo", "pagina", "confianza"]
    with path.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        for fila in filas(grupos):
            escritor.writerow({clave: fila[clave] for clave in columnas})
    return path


def escribir_docx(
    grupos: list[Grupo],
    path: Path,
    *,
    titulo: str = "Individualizacion de documentos",
    perfil: Perfil | None = None,
) -> Path:
    """Escribe la tabla de individualizacion en Word (insumo del escrito)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    perfil = perfil or (grupos[0]._perfil if grupos else get_perfil())
    columnas = perfil.columnas()

    documento = DocxDocument()
    documento.add_heading(titulo, level=1)
    documento.add_paragraph(
        f"Total de documentos: {len(grupos)}. "
        "Las fechas van en orden cronologico; los documentos sin fecha legible "
        "quedan al final."
    )

    tabla = documento.add_table(rows=1, cols=len(columnas))
    tabla.style = "Table Grid"
    for celda, (_, etiqueta) in zip(tabla.rows[0].cells, columnas):
        celda.text = ""
        corrida = celda.paragraphs[0].add_run(etiqueta)
        corrida.bold = True
        corrida.font.size = Pt(9)

    for fila in filas(grupos):
        celdas = tabla.add_row().cells
        for celda, (clave, _) in zip(celdas, columnas):
            celda.text = ""
            corrida = celda.paragraphs[0].add_run(fila[clave] or "-")
            corrida.font.size = Pt(9)

    documento.save(str(path))
    return path
