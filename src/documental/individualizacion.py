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


def _compatible(tipo_a: str, tipo_b: str) -> bool:
    """True si dos bloques pueden ser partes del mismo documento fisico."""
    if tipo_a == tipo_b:
        return True
    genericos = {T_FICHA, T_SIN_CLASIFICAR}
    return tipo_a in genericos or tipo_b in genericos


def _sin_conflicto(anteriores: list[Document], posteriores: list[Document]) -> bool:
    """True si los bloques no se contradicen en folio ni en RUT del titular."""
    folios_a = {_texto(d.folio) for d in anteriores if _texto(d.folio)}
    folios_b = {_texto(d.folio) for d in posteriores if _texto(d.folio)}
    if folios_a and folios_b and not (folios_a & folios_b):
        return False
    ruts_a = {rut for rut in (_rut_de(d) for d in anteriores) if rut}
    ruts_b = {rut for rut in (_rut_de(d) for d in posteriores) if rut}
    if ruts_a and ruts_b and not (ruts_a & ruts_b):
        return False
    return True


def _unidades_de_hoja(bloques: list[Document]) -> list[list[Document]]:
    """Consolida los bloques de una misma hoja en documentos fisicos.

    El layout parte una hoja en varios bloques (columnas, tablas, un pie de
    pagina suelto), pero en una ficha clinica esos bloques son partes del mismo
    documento y no documentos distintos. En cambio, dos bonos en la misma hoja
    si son dos documentos: se distinguen porque tienen folios distintos.

    Los bloques que no se pudieron clasificar se adhieren a la categoria
    dominante de la hoja, porque un fragmento sin texto utilizable no constituye
    un documento autonomo.
    """
    tipos = [tipo_canonico(d) for d in bloques]
    categorias = [categoria_de(d) for d in bloques]
    dominante = next((c for c in categorias if c != CAT_OTROS), "")
    asignadas = [
        dominante
        if (categoria == CAT_OTROS and tipo == T_SIN_CLASIFICAR and dominante)
        else categoria
        for categoria, tipo in zip(categorias, tipos)
    ]

    unidades: list[tuple[str, list[Document]]] = []
    for bloque, categoria in zip(bloques, asignadas):
        if (
            unidades
            and unidades[-1][0] == categoria
            and _sin_conflicto(unidades[-1][1], [bloque])
        ):
            unidades[-1][1].append(bloque)
        else:
            unidades.append((categoria, [bloque]))
    return [documentos for _, documentos in unidades]


def _continua(anteriores: list[Document], posteriores: list[Document]) -> bool:
    """True si ``posteriores`` es la hoja siguiente del mismo documento."""
    ultimo = anteriores[-1]
    primero = posteriores[0]
    if ultimo.source_file != primero.source_file:
        return False
    if primero.page != ultimo.page + 1 or primero.index_in_page != 1:
        return False

    categoria = categoria_de(ultimo)
    if categoria != categoria_de(primero):
        return False
    if not _compatible(tipo_canonico(ultimo), tipo_canonico(primero)):
        return False
    if not _sin_conflicto(anteriores, posteriores):
        return False

    # Un documento sin clasificar puede ser cualquier cosa: solo se une con una
    # senal explicita (mismo folio o mismo RUT) que lo justifique.
    if (
        tipo_canonico(ultimo) == T_SIN_CLASIFICAR
        and tipo_canonico(primero) == T_SIN_CLASIFICAR
    ):
        folios = {_texto(d.folio) for d in anteriores + posteriores if _texto(d.folio)}
        ruts = {rut for rut in (_rut_de(d) for d in anteriores + posteriores) if rut}
        return len(folios) == 1 or len(ruts) == 1
    return True


@dataclass
class Grupo:
    """Un documento fisico: una o mas paginas que se presentan como una unidad."""

    numero: int
    documentos: list[Document] = field(default_factory=list)

    @property
    def primero(self) -> Document:
        return self.documentos[0]

    @property
    def archivo(self) -> str:
        return self.primero.source_file

    @property
    def paginas(self) -> list[int]:
        return sorted({doc.page for doc in self.documentos})

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
        return tipo_de_grupo(self.documentos)

    @property
    def categoria(self) -> str:
        """Categoria (bonos, boletas, fichas, recetas, certificados, otros).

        Se deriva del tipo del grupo y no del primer bloque: una hoja cuyo
        encabezado el OCR no pudo leer no debe arrastrar el documento entero a
        la carpeta de "otros".
        """
        return categoria_de_tipo(tipo_de_grupo(self.documentos))

    @property
    def detalle(self) -> str:
        """Elementos propios de la categoria (prestador, detalle de compra...)."""
        for documento in self.documentos:
            texto = detalle_de(documento)
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
        peor = self.primero.confianza_global()
        for documento in self.documentos[1:]:
            otra = documento.confianza_global()
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


def agrupar(documentos: list[Document]) -> list[Grupo]:
    """Agrupa y numera los documentos en orden cronologico.

    El proceso va de lo chico a lo grande: primero se consolidan los bloques de
    una misma hoja (que el layout puede haber partido en columnas o haber
    dejado con un pie de pagina suelto) y despues se unen las hojas
    consecutivas que pertenecen al mismo documento.
    """
    ordenados = sorted(
        documentos, key=lambda d: (d.source_file, d.page, d.index_in_page)
    )

    hojas: dict[tuple[str, int], list[Document]] = {}
    for documento in ordenados:
        hojas.setdefault((documento.source_file, documento.page), []).append(documento)

    unidades: list[list[Document]] = []
    for clave in hojas:  # el dict conserva el orden de insercion
        unidades.extend(_unidades_de_hoja(hojas[clave]))

    bloques: list[list[Document]] = []
    for unidad in unidades:
        if bloques and _continua(bloques[-1], unidad):
            bloques[-1].extend(unidad)
        else:
            bloques.append(list(unidad))

    bloques = [bloque for bloque in bloques if bloque]
    bloques.sort(key=_clave_cronologica)
    return [
        Grupo(numero=numero, documentos=bloque)
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
                "categoria": CATEGORIA_ETIQUETA.get(grupo.categoria, grupo.categoria),
                "tipo": grupo.tipo,
                "fecha": grupo.fecha_texto,
                "emisor": grupo.valor("emisor_nombre"),
                "rut_emisor": grupo.valor("emisor_rut"),
                "titular": grupo.valor("titular_nombre"),
                "rut_titular": grupo.valor("titular_rut"),
                "folio": grupo.valor("folio"),
                "monto_total": format_clp(int(monto)) if monto.isdigit() else monto,
                "detalle": grupo.detalle,
                "archivo": grupo.archivo,
                "pagina": grupo.paginas_texto,
                "confianza": grupo.confianza,
                "etiqueta": grupo.etiqueta,
            }
        )
    return resultado


def escribir_csv(grupos: list[Grupo], path: Path) -> Path:
    """Escribe la tabla de individualizacion en CSV.

    Separador ``;`` y BOM de UTF-8 para que Excel en espanol lo abra en columnas
    sin pasos adicionales.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columnas = [clave for clave, _ in COLUMNAS] + ["archivo", "pagina", "confianza"]
    with path.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas, delimiter=";")
        escritor.writeheader()
        for fila in filas(grupos):
            escritor.writerow({clave: fila[clave] for clave in columnas})
    return path


def escribir_docx(
    grupos: list[Grupo], path: Path, *, titulo: str = "Individualizacion de documentos"
) -> Path:
    """Escribe la tabla de individualizacion en Word (insumo del escrito)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    documento = DocxDocument()
    documento.add_heading(titulo, level=1)
    documento.add_paragraph(
        f"Total de documentos: {len(grupos)}. "
        "Las fechas van en orden cronologico; los documentos sin fecha legible "
        "quedan al final."
    )

    tabla = documento.add_table(rows=1, cols=len(COLUMNAS))
    tabla.style = "Table Grid"
    for celda, (_, etiqueta) in zip(tabla.rows[0].cells, COLUMNAS):
        celda.text = ""
        corrida = celda.paragraphs[0].add_run(etiqueta)
        corrida.bold = True
        corrida.font.size = Pt(9)

    for fila in filas(grupos):
        celdas = tabla.add_row().cells
        for celda, (clave, _) in zip(celdas, COLUMNAS):
            celda.text = ""
            corrida = celda.paragraphs[0].add_run(fila[clave] or "-")
            corrida.font.size = Pt(9)

    documento.save(str(path))
    return path
