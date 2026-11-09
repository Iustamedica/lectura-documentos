"""Generacion del informe Word a partir del expediente revisado.

El informe esta pensado para el abogado: portada, resumen por titular, tabla
consolidada de documentos, fichas individuales por documento (con recorte de
imagen cuando existe) y un anexo de datos a verificar.

La fuente de verdad es el JSON del expediente, de modo que cualquier correccion
hecha en el revisor HTML se refleja al regenerar el documento.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from docx import Document as DocxDocument
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from .classify import FAMILY_LABELS
from .models import (
    CONF_ALTA,
    CONF_BAJA,
    CONF_FALTA,
    CONF_MEDIA,
    Document,
    Expediente,
    Titular,
)
from .normalizers import format_clp
from .titulares import assign_titular

CONFIDENCE_LABELS = {
    CONF_ALTA: "Verificado",
    CONF_MEDIA: "Probable",
    CONF_BAJA: "Verificar",
    CONF_FALTA: "Faltante",
}

# Color de la etiqueta de confianza en el informe (RGB).
CONFIDENCE_COLORS = {
    CONF_ALTA: RGBColor(0x1E, 0x6B, 0x33),
    CONF_MEDIA: RGBColor(0x8A, 0x5A, 0x00),
    CONF_BAJA: RGBColor(0xB0, 0x2A, 0x2A),
    CONF_FALTA: RGBColor(0x66, 0x66, 0x66),
}

# Etiquetas legibles de los campos del documento.
FIELD_LABELS = {
    "tipo_documento": "Tipo de documento",
    "folio": "Folio / numero",
    "emisor_nombre": "Emisor",
    "emisor_rut": "RUT emisor",
    "emisor_giro": "Giro",
    "emisor_direccion": "Direccion emisor",
    "titular_nombre": "Titular",
    "titular_rut": "RUT titular",
    "titular_edad": "Edad",
    "titular_direccion": "Direccion titular",
    "titular_contacto": "Contacto",
    "titular_prevision": "Prevision",
    "profesional_nombre": "Profesional",
    "profesional_rut": "RUT profesional",
    "profesional_especialidad": "Especialidad",
    "fecha_emision": "Fecha emision",
    "fecha_atencion": "Fecha atencion",
    "fecha_vencimiento": "Fecha vencimiento",
    "hora": "Hora",
    "monto_bruto": "Monto bruto",
    "monto_bonificacion": "Bonificacion",
    "monto_copago": "Copago",
    "monto_neto": "Neto",
    "monto_iva": "IVA",
    "monto_total": "Total",
    "medio_pago": "Medio de pago",
    "diagnostico": "Diagnostico",
    "observaciones": "Observaciones",
}

AMOUNT_FIELDS = {
    "monto_bruto",
    "monto_bonificacion",
    "monto_copago",
    "monto_neto",
    "monto_iva",
    "monto_total",
}


def _set_cell_background(cell, color_hex: str) -> None:
    """Pinta el fondo de una celda (no hay API directa en python-docx)."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color_hex)
    tc_pr.append(shd)


def _format_value(name: str, value) -> str:
    """Formatea el valor de un campo para mostrarlo en el informe."""
    if value in (None, "", [], {}):
        return "-"
    if name in AMOUNT_FIELDS:
        return format_clp(value if isinstance(value, int) else None) or str(value)
    return str(value)


def _confidence_run(paragraph, confidence: str):
    """Agrega al parrafo una marca de confianza con color."""
    run = paragraph.add_run(f" [{CONFIDENCE_LABELS.get(confidence, confidence)}]")
    run.font.size = Pt(8)
    run.font.color.rgb = CONFIDENCE_COLORS.get(confidence, RGBColor(0, 0, 0))
    run.italic = True
    return run


def _add_heading(doc: DocxDocument, text: str, level: int = 1) -> None:
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)


def _build_cover(doc: DocxDocument, expediente: Expediente, perfil=None) -> None:
    """Portada del informe."""
    from .perfiles import get_perfil

    perfil = perfil or get_perfil()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run(perfil.titulo_informe)
    run.bold = True
    run.font.size = Pt(20)
    run.font.color.rgb = RGBColor(0x1F, 0x3A, 0x5F)

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub = subtitle.add_run("Expediente: " + Path(expediente.carpeta).name)
    sub.font.size = Pt(13)

    doc.add_paragraph()

    info = doc.add_table(rows=0, cols=2)
    info.style = "Table Grid"
    info.alignment = WD_TABLE_ALIGNMENT.CENTER
    rows = [
        ("Carpeta de origen", expediente.carpeta),
        ("Documentos analizados", str(len(expediente.documentos))),
        (
            "Partes identificadas" if not perfil.usa_titulares else "Titulares identificados",
            str(len(expediente.titulares)),
        ),
        ("Fecha de generacion", datetime.now().strftime("%d-%m-%Y %H:%M")),
        ("Procesamiento", "OCR local (RapidOCR / ONNX Runtime) + revision asistida"),
    ]
    for label, value in rows:
        cells = info.add_row().cells
        cells[0].text = label
        cells[1].text = value
        cells[0].paragraphs[0].runs[0].bold = True
        _set_cell_background(cells[0], "EDF1F7")

    doc.add_paragraph()
    aviso = doc.add_paragraph()
    aviso_run = aviso.add_run(
        "Los datos fueron obtenidos por reconocimiento optico de caracteres (OCR) sobre "
        "documentos escaneados. Cada dato incluye una marca de confianza; los marcados "
        "como 'Verificar' o 'Faltante' deben contrastarse con el documento original "
        "antes de su uso judicial o administrativo."
    )
    aviso_run.italic = True
    aviso_run.font.size = Pt(9)
    doc.add_page_break()


def _doc_total(doc: Document) -> int | None:
    """Monto total del documento: usa el total o el mayor monto disponible."""
    if isinstance(doc.monto_total.value, int):
        return doc.monto_total.value
    for name in ("monto_copago", "monto_bruto", "monto_neto"):
        value = doc.field(name).value
        if isinstance(value, int):
            return value
    return None


def _build_summary(doc: DocxDocument, expediente: Expediente, perfil=None) -> None:
    """Resumen por titular (salud) o por categoria (legal)."""
    from .perfiles import get_perfil

    perfil = perfil or get_perfil()
    if not perfil.usa_titulares:
        _build_category_summary(doc, expediente, perfil)
        return
    _add_heading(doc, "1. Resumen por titular", 1)

    if not expediente.titulares:
        doc.add_paragraph("No se identificaron titulares en los documentos analizados.")
        return

    table = doc.add_table(rows=1, cols=5)
    table.style = "Table Grid"
    header = table.rows[0].cells
    for cell, text in zip(header, ("Titular", "RUT", "Relacion", "Documentos", "Total $ (CLP)")):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        _set_cell_background(cell, "1F3A5F")
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for titular in expediente.titulares:
        docs_titular = [d for d in expediente.documentos if assign_titular(d, [titular])]
        total = sum(_doc_total(d) or 0 for d in docs_titular)
        cells = table.add_row().cells
        cells[0].text = titular.nombre or "(sin nombre)"
        cells[1].text = titular.rut or "POR CONFIRMAR"
        cells[2].text = titular.relacion or "-"
        cells[3].text = str(len(docs_titular))
        cells[4].text = format_clp(total) if total else "-"
        if not titular.rut:
            # Un RUT no verificado no puede leerse como un dato consolidado.
            for run in cells[1].paragraphs[0].runs:
                run.bold = True
                run.font.color.rgb = CONFIDENCE_COLORS[CONF_BAJA]
            titular.notas = titular.notas or "RUT no verificado en los documentos aportados."

    total_general = sum(_doc_total(d) or 0 for d in expediente.documentos)
    parrafo = doc.add_paragraph()
    parrafo.add_run("Total general documentado: ").bold = True
    parrafo.add_run(format_clp(total_general))

    sin_titular = [
        d for d in expediente.documentos
        if assign_titular(d, expediente.titulares) is None
    ]
    if sin_titular:
        nota = doc.add_paragraph()
        run = nota.add_run(
            f"{len(sin_titular)} documento(s) no pudieron asociarse a un titular identificado "
            "y se listan en el anexo de verificacion."
        )
        run.italic = True
        run.font.color.rgb = CONFIDENCE_COLORS[CONF_BAJA]


def _valor(item: Document, nombre: str) -> str:
    """Valor de un campo (comun o del perfil) como texto."""
    valor = item.field(nombre).value
    if valor in (None, "", [], {}):
        return ""
    return str(valor)


def _fecha_item(item: Document) -> str:
    for nombre in ("fecha_emision", "fecha_atencion", "fecha_vencimiento"):
        valor = _valor(item, nombre)
        if valor:
            return valor
    return "-"


def _build_category_summary(doc: DocxDocument, expediente: Expediente, perfil) -> None:
    """Resumen por categoria documental (perfiles sin titulares, como legal)."""
    _add_heading(doc, "1. Resumen por categoria", 1)

    conteo: dict[str, int] = {}
    for item in expediente.documentos:
        clave = perfil.categoria_de_tipo(perfil.tipo_canonico(item))
        conteo[clave] = conteo.get(clave, 0) + 1

    if not conteo:
        doc.add_paragraph("No se detectaron documentos clasificables en la carpeta.")
        return

    table = doc.add_table(rows=1, cols=3)
    table.style = "Table Grid"
    header = table.rows[0].cells
    for cell, text in zip(header, ("Categoria", "Carpeta", "Documentos")):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        _set_cell_background(cell, "1F3A5F")
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for categoria in perfil.categorias:
        total = conteo.get(categoria.clave, 0)
        cells = table.add_row().cells
        cells[0].text = categoria.etiqueta
        cells[1].text = categoria.carpeta
        cells[2].text = str(total)

    doc.add_paragraph()


def _build_index_table(
    doc: DocxDocument, expediente: Expediente, perfil=None
) -> None:
    """Tabla consolidada de todos los documentos del expediente."""
    from .perfiles import get_perfil

    perfil = perfil or get_perfil()
    _add_heading(doc, "2. Indice de documentos", 1)

    if perfil.usa_titulares:
        headers = (
            "N", "Tipo de documento", "Titular", "RUT", "Fecha", "Emisor", "Total $", "Estado",
        )
    else:
        headers = (
            "N", "Tipo de documento", "ROL / RIT", "Tribunal", "Caratula", "Fecha", "Parte", "Estado",
        )
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, headers):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8)
        _set_cell_background(cell, "1F3A5F")
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for number, item in enumerate(expediente.documentos, start=1):
        cells = table.add_row().cells
        if perfil.usa_titulares:
            values = (
                str(number),
                item.tipo_documento.value or FAMILY_LABELS.get(item.familia, item.familia),
                item.titular_nombre.value or "-",
                item.titular_rut.value or "-",
                item.fecha_emision.value or item.fecha_atencion.value or "-",
                item.emisor_nombre.value or "-",
                format_clp(_doc_total(item)) or "-",
                CONFIDENCE_LABELS.get(
                    item.confianza_global(perfil.criticos_de(item)), "-"
                ),
            )
        else:
            values = (
                str(number),
                item.tipo_documento.value or perfil.tipo_canonico(item),
                _valor(item, "rol") or "-",
                _valor(item, "tribunal") or "-",
                _valor(item, "caratula") or "-",
                _fecha_item(item),
                _valor(item, "parte_demandante") or "-",
                CONFIDENCE_LABELS.get(
                    item.confianza_global(perfil.criticos_de(item)), "-"
                ),
            )
        for cell, value in zip(cells, values):
            cell.text = str(value)
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(8)
        estado = item.confianza_global(perfil.criticos_de(item))
        if estado in (CONF_BAJA, CONF_FALTA):
            _set_cell_background(cells[-1], "FDE7E7")

    doc.add_paragraph()
    leyenda = doc.add_paragraph()
    leyenda_run = leyenda.add_run(
        "Estado del documento: Verificado = campos criticos con lectura segura; "
        "Probable = lectura consistente pero no validada; Verificar = requiere "
        "contraste con el original; Faltante = no fue posible obtener el dato."
    )
    leyenda_run.italic = True
    leyenda_run.font.size = Pt(8)
    doc.add_page_break()


def _build_document_card(
    doc: DocxDocument,
    item: Document,
    number: int,
    image_root: Path | None,
    incluir_imagenes: bool = False,
    perfil=None,
) -> None:
    """Ficha individual de un documento con sus datos y, si se pide, su recorte."""
    from .perfiles import get_perfil

    perfil = perfil or get_perfil()
    _add_heading(doc, f"3.{number} {item.titulo or item.tipo_documento.value}", 2)

    origen = doc.add_paragraph()
    origen.add_run("Archivo: ").bold = True
    origen.add_run(f"{item.source_file} (pagina {item.page}, bloque {item.index_in_page})")
    origen.add_run("   Familia: ").bold = True
    origen.add_run(perfil.etiqueta_familia(item.familia))

    estado = doc.add_paragraph()
    estado.add_run("Estado de lectura: ").bold = True
    estado.add_run(CONFIDENCE_LABELS.get(item.confianza_global(perfil.criticos_de(item)), "-"))
    if item.familia_confianza == CONF_BAJA:
        estado.add_run("  (familia documental inferida, revisar)").italic = True

    table = doc.add_table(rows=0, cols=3)
    table.style = "Table Grid"
    etiquetas = dict(FIELD_LABELS)
    etiquetas.update(perfil.etiquetas_campo())
    campos = list(item.fields().items()) + list(item.extra.items())
    for name, field in campos:
        if field.is_empty and field.confidence == CONF_FALTA:
            continue
        cells = table.add_row().cells
        cells[0].text = etiquetas.get(name, name)
        cells[0].paragraphs[0].runs[0].bold = True
        cells[0].paragraphs[0].runs[0].font.size = Pt(9)
        _set_cell_background(cells[0], "F2F5F9")
        cells[1].text = _format_value(name, field.value)
        cells[1].paragraphs[0].runs[0].font.size = Pt(9)
        marker = cells[2].paragraphs[0]
        _confidence_run(marker, field.confidence)
        if field.edited:
            edited_run = marker.add_run(" corregido")
            edited_run.font.size = Pt(8)
            edited_run.font.color.rgb = RGBColor(0x1E, 0x6B, 0x33)
        if field.note:
            note_run = marker.add_run(" " + field.note)
            note_run.font.size = Pt(8)
            note_run.italic = True

    if item.items:
        doc.add_paragraph()
        items_title = doc.add_paragraph()
        items_title.add_run("Prestaciones / productos").bold = True
        items_table = doc.add_table(rows=1, cols=4)
        items_table.style = "Table Grid"
        for cell, text in zip(items_table.rows[0].cells, ("Descripcion", "Cant.", "Unitario", "Total")):
            cell.text = text
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].runs[0].font.size = Pt(8)
            _set_cell_background(cell, "EDF1F7")
        for line_item in item.items:
            cells = items_table.add_row().cells
            cells[0].text = line_item.descripcion or "-"
            cells[1].text = line_item.cantidad or "-"
            cells[2].text = format_clp(line_item.valor_unitario) or "-"
            cells[3].text = format_clp(line_item.total) or "-"
            for cell in cells:
                for run in cell.paragraphs[0].runs:
                    run.font.size = Pt(8)

    if incluir_imagenes and item.imagen and image_root:
        image_path = Path(image_root) / item.imagen
        if image_path.exists():
            doc.add_paragraph()
            caption = doc.add_paragraph()
            caption.add_run("Recorte del documento original").italic = True
            caption.runs[0].font.size = Pt(8)
            try:
                doc.add_picture(str(image_path), width=Cm(15.5))
            except Exception:
                doc.add_paragraph(f"(No se pudo insertar la imagen {item.imagen})")

    doc.add_page_break()


def _build_verification_annex(
    doc: DocxDocument, expediente: Expediente, perfil=None
) -> None:
    """Anexo con los datos que requieren contraste con el original."""
    from .perfiles import get_perfil

    perfil = perfil or get_perfil()
    etiquetas = dict(FIELD_LABELS)
    etiquetas.update(perfil.etiquetas_campo())
    _add_heading(doc, "4. Anexo de verificacion", 1)

    pendientes: list[tuple[Document, str, str, str]] = []
    for item in expediente.documentos:
        for name in item.campos_a_revisar(perfil.criticos_de(item)):
            field = item.field(name)
            pendientes.append(
                (item, etiquetas.get(name, name), _format_value(name, field.value), field.note)
            )

    # Documentos sin titular asociado.
    huerfanos = [
        item for item in expediente.documentos
        if assign_titular(item, expediente.titulares) is None
    ]
    for item in huerfanos:
        pendientes.append(
            (item, "Titular no identificado", item.titular_nombre.value or "-",
             "Asociar manualmente a un titular del expediente")
        )

    if not pendientes:
        doc.add_paragraph(
            "No hay datos pendientes: todos los campos criticos quedaron verificados."
        )
        return

    intro = doc.add_paragraph()
    intro.add_run(
        f"Se identificaron {len(pendientes)} dato(s) que requieren contraste con el "
        "documento original:"
    )

    table = doc.add_table(rows=1, cols=4)
    table.style = "Table Grid"
    for cell, text in zip(table.rows[0].cells, ("Documento", "Campo", "Valor leido", "Observacion")):
        cell.text = text
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(8)
        _set_cell_background(cell, "1F3A5F")
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    for item, campo, valor, nota in pendientes:
        cells = table.add_row().cells
        cells[0].text = f"{item.titulo or item.doc_id} ({item.source_file} p.{item.page})"
        cells[1].text = campo
        cells[2].text = valor
        cells[3].text = nota or "-"
        for cell in cells:
            for run in cell.paragraphs[0].runs:
                run.font.size = Pt(8)

    if expediente.advertencias:
        doc.add_paragraph()
        _add_heading(doc, "Advertencias del procesamiento", 2)
        for warning in expediente.advertencias:
            doc.add_paragraph(warning, style="List Bullet")


def _configure_page(doc: DocxDocument) -> None:
    """Configura tamano de pagina, margenes y estilo base."""
    section = doc.sections[0]
    section.orientation = WD_ORIENT.PORTRAIT
    section.page_width = Cm(21.59)
    section.page_height = Cm(27.94)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)


def generar_informe(
    expediente: Expediente,
    destino: Path,
    *,
    image_root: Path | None = None,
    incluir_imagenes: bool = False,
    perfil=None,
) -> Path:
    """Genera el informe Word y devuelve la ruta del archivo creado.

    Por defecto **no** inserta los recortes de las imagenes: el informe es el
    documento de trabajo y las imagenes ya estan en el PDF compilado del
    tribunal. Sin recortes el Word pasa de ~100 MB a ~1 MB y se puede enviar por
    correo. Con ``incluir_imagenes=True`` se anexan las imagenes (util solo para
    revisar a pantalla).
    """
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)

    doc = DocxDocument()
    _configure_page(doc)
    _build_cover(doc, expediente, perfil)
    _build_summary(doc, expediente, perfil)
    _build_index_table(doc, expediente, perfil)

    _add_heading(doc, "3. Fichas por documento", 1)
    if incluir_imagenes:
        doc.add_paragraph(
            "Cada ficha reproduce los datos extraidos del documento, su nivel de "
            "confianza y el recorte de la imagen original."
        )
    else:
        doc.add_paragraph(
            "Cada ficha reproduce los datos extraidos del documento y su nivel de "
            "confianza. Las imagenes de los documentos estan en el PDF compilado."
        )
    for number, item in enumerate(expediente.documentos, start=1):
        _build_document_card(doc, item, number, image_root, incluir_imagenes, perfil)

    _build_verification_annex(doc, expediente, perfil)

    footer = doc.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run(
        f"Informe generado el {datetime.now().strftime('%d-%m-%Y %H:%M')} - "
        "Documentos obtenidos por OCR, verificar los datos marcados."
    )
    footer_run.font.size = Pt(8)
    footer_run.italic = True

    doc.save(str(destino))
    return destino




