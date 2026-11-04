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

from .models import CONFIDENCE_ORDER, Document
from .normalizers import format_clp, format_date_cl, parse_date, rut_body

# Campos que se prueban, en este orden, para fechar un documento.
CAMPOS_FECHA = ("fecha_emision", "fecha_atencion", "fecha_vencimiento")

# Columnas de la tabla de individualizacion (orden del escrito).
COLUMNAS = (
    ("N", "N"),
    ("tipo", "Documento"),
    ("fecha", "Fecha"),
    ("emisor", "Emisor"),
    ("titular", "Titular"),
    ("rut_titular", "RUT"),
    ("folio", "Folio"),
    ("monto_total", "Monto"),
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


def _continua(anterior: Document, actual: Document) -> bool:
    """True si ``actual`` parece la hoja siguiente del mismo documento."""
    if anterior.source_file != actual.source_file:
        return False
    if actual.page != anterior.page + 1 or actual.index_in_page != 1:
        return False
    if anterior.familia != actual.familia:
        return False

    folio_a = _texto(anterior.folio)
    folio_b = _texto(actual.folio)
    if folio_a and folio_b and folio_a != folio_b:
        return False

    rut_a, rut_b = _rut_de(anterior), _rut_de(actual)
    if rut_a and rut_b and rut_a != rut_b:
        return False

    # Un documento sin clasificar puede ser cualquier cosa: solo se une si hay
    # una senal explicita (mismo folio o mismo RUT) que lo justifique.
    if anterior.familia == "desconocido":
        mismo_folio = bool(folio_a) and folio_a == folio_b
        mismo_rut = bool(rut_a) and rut_a == rut_b
        return mismo_folio or mismo_rut
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
        tipo = self.valor("tipo_documento")
        if tipo:
            return tipo
        from .classify import FAMILY_LABELS

        return FAMILY_LABELS.get(self.primero.familia, self.primero.familia)

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
    """Agrupa y numera los documentos en orden cronologico."""
    ordenados = sorted(
        documentos, key=lambda d: (d.source_file, d.page, d.index_in_page)
    )
    bloques: list[list[Document]] = []
    for documento in ordenados:
        if bloques and _continua(bloques[-1][-1], documento):
            bloques[-1].append(documento)
        else:
            bloques.append([documento])
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
                "tipo": grupo.tipo,
                "fecha": grupo.fecha_texto,
                "emisor": grupo.valor("emisor_nombre"),
                "rut_emisor": grupo.valor("emisor_rut"),
                "titular": grupo.valor("titular_nombre"),
                "rut_titular": grupo.valor("titular_rut"),
                "folio": grupo.valor("folio"),
                "monto_total": format_clp(int(monto)) if monto.isdigit() else monto,
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
