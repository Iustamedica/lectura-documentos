"""Pipeline de punta a punta: PDF -> documentos -> expediente.

Flujo:
  1. OCR de cada pagina (ocr.py).
  2. Reconstruccion de lineas y separacion en bloques/documentos (layout.py).
  3. Clasificacion por familia (classify.py).
  4. Extraccion de campos con el extractor de la familia (extractors/).
  5. Agrupacion por titular y advertencias (titulares.py).

Todo es determinista y sin red: el resultado se puede revisar y corregir luego
en el revisor HTML antes de generar el Word definitivo.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .classify import FARMACIA, classify
from .extractors import get_extractor
from .extractors.otros import extract_clinico, extract_receta_manuscrita
from .layout import Block, build_lines, split_blocks
from .models import CONF_BAJA, CONF_FALTA, CONF_MEDIA, Document
from .normalizers import fold, parse_clp
from .ocr import TARGET_HEIGHT, OCREngine, PageOCR, ocr_pages
from .titulares import TitularConfig, resolve_expediente

# Marcadores que indican el inicio de un documento dentro de una hoja.
DOC_MARKERS = (
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

# Encabezados/pies que no constituyen un documento por si mismos.
_NOISE_ONLY = (
    "fondo nacional de salud",
    "servicio de impuestos internos",
    "timbre electronico",
)

MIN_BLOCK_LINES = 2


@dataclass
class PipelineOptions:
    """Opciones de ejecucion configurables por linea de comandos."""

    render_dir: Path | None = None    # carpeta donde guardar los recortes PNG
    dpi: int = 300
    min_confidence: float = 0.35      # descarta tokens de OCR muy malos
    # Alto al que se normaliza la imagen antes del OCR. Reduce las fotos de
    # celular de ~12 MP: acota el uso de memoria, aunque la ganancia de
    # velocidad es pequena (~10 %) porque RapidOCR normaliza el tamano interno.
    target_height: int = TARGET_HEIGHT


def _is_noise(block: Block) -> bool:
    """True si el bloque es ruido (encabezado/pie suelto, casi sin texto).

    Un solo renglon puede ser un documento valido (por ejemplo un bono FONASA
    escaneado en una sola linea), por lo que solo se descarta cuando el bloque
    no tiene ninguna linea con contenido util.
    """
    meaningful = [
        line
        for line in block.lines
        if len(line.text.strip()) >= 4
        and not any(fold(line.text).startswith(noise) for noise in _NOISE_ONLY)
    ]
    return not meaningful


def _block_family(block: Block) -> tuple[str, str, str]:
    """Familia, confianza y texto del bloque."""
    text = block.text
    result = classify(text)
    familia = result.familia
    folded = fold(text)
    # Una receta de farmacia no es una receta optica.
    if familia == FARMACIA and "receta" in folded and "farmacia" not in folded:
        familia = "receta_optica"
    # Voucher de tarjeta (Transbank/KLAP) que acompana a una boleta: no es un
    # documento autonomo y su "titular" seria el nombre del comercio.
    if _is_payment_voucher(folded):
        familia = "comprobante_pago"
    # Receta manuscrita del oftalmologo: texto corto, "Rp." y datos del medico.
    if familia == "documento_clinico" and _looks_like_manuscrita(folded):
        familia = "receta_manuscrita"
    return familia, result.confianza, text


def _is_payment_voucher(folded: str) -> bool:
    """True si el bloque es el comprobante de una transaccion con tarjeta."""
    marcadores = ("transbank", "klap", "tarjeta de debito", "tarjeta-de debito", "valido como boleta")
    return sum(1 for m in marcadores if m in folded) >= 2


def _looks_like_manuscrita(folded: str) -> bool:
    """True si el bloque parece una receta escrita a mano por el oftalmologo."""
    if "rp." not in folded and "receta" not in folded:
        return False
    return "oftalmolog" in folded or "vision en familia" in folded


def _crop_block(page: PageOCR, block: Block, dest: Path) -> str:
    """Guarda el recorte del bloque como PNG y devuelve el nombre del archivo."""
    margin = 12
    left = max(0, int(min(line.x0 for line in block.lines) - margin))
    right = min(page.image.width, int(max(line.x1 for line in block.lines) + margin))
    top = max(0, int(block.y0 - margin))
    bottom = min(page.image.height, int(block.y1 + margin))
    if right - left < 40 or bottom - top < 40:
        return ""
    crop = page.image.crop((left, top, right, bottom))
    dest.parent.mkdir(parents=True, exist_ok=True)
    crop.save(dest, format="PNG", optimize=True)
    return dest.name


def process_pdf(
    path: Path,
    engine: OCREngine | None = None,
    options: PipelineOptions | None = None,
    nombres_conocidos: list[str] | None = None,
) -> list[Document]:
    """Procesa un archivo y devuelve los documentos detectados."""
    options = options or PipelineOptions()
    pages = ocr_pages(path, engine, dpi=options.dpi, target_height=options.target_height)
    documents: list[Document] = []
    for page in pages:
        documents.extend(process_page(path, page, options, nombres_conocidos, documents))
    return documents


def process_page(
    path: Path,
    page: PageOCR,
    options: PipelineOptions,
    nombres_conocidos: list[str] | None,
    documentos_previos: list[Document] | None = None,
) -> list[Document]:
    """Procesa una pagina ya renderizada y con OCR hecho.

    Se separa de `process_pdf` para poder reutilizar el resultado del OCR en la
    segunda pasada (recetas manuscritas) sin volver a leer el PDF completo.
    """
    tokens = [t for t in page.tokens if t.score >= options.min_confidence]
    lines = build_lines(tokens)
    if not lines:
        return []

    blocks = split_blocks(
        lines, page_height=page.height, gap_ratio=0.05, markers=DOC_MARKERS
    )
    blocks = [block for block in blocks if not _is_noise(block)]

    documents: list[Document] = []
    for index, block in enumerate(blocks, start=1):
        familia, confianza, text = _block_family(block)
        doc_id = f"{path.stem[:28]}-p{page.page}-{index}"

        if familia == "comprobante_pago":
            # El voucher se adjunta al ultimo documento, sea de esta pagina o
            # de la anterior (las boletas suelen traer el voucher en la pagina 2).
            destino = documents or documentos_previos or []
            _attach_payment_voucher(block, destino)
            continue

        doc = Document(
            doc_id=doc_id,
            source_file=path.name,
            page=page.page,
            index_in_page=index,
            familia=familia,
            familia_confianza=confianza,
            texto_ocr=text,
        )
        try:
            if familia == "receta_manuscrita":
                extract_receta_manuscrita(block, doc, nombres_conocidos)
            elif familia == "documento_clinico":
                # En formularios clinicos el paciente tambien puede ser manuscrito.
                extract_clinico(block, doc, nombres_conocidos)
            else:
                get_extractor(familia)(block, doc)
        except Exception as error:  # un extractor nunca debe abortar el lote
            doc.observaciones.set(
                f"Error del extractor {familia}: {error}", CONF_BAJA, ""
            )
        if not doc.titulo:
            doc.titulo = f"Documento {index} (p. {page.page})"
        if options.render_dir:
            doc.imagen = _crop_block(
                page, block, Path(options.render_dir) / f"{doc_id}.png"
            )
        documents.append(doc)
    _propagar_folio(documents)
    return documents


def _propagar_folio(documents: list[Document]) -> None:
    """Hereda el numero de identificacion entre bloques de la misma hoja.

    Una hoja puede partirse en varios bloques (una foto rotada, una tabla que el
    layout separa en columnas). El folio o numero de identificacion suele quedar
    en uno solo de esos bloques y los demas son partes del mismo documento.

    Se propaga solo cuando **todos** los folios presentes en la hoja coinciden:
    si hay dos folios distintos son dos documentos (por ejemplo dos bonos en la
    misma hoja) y no se toca nada. El valor heredado queda con confianza media y
    una nota para que se pueda contrastar.
    """
    por_hoja: dict[tuple[str, int], list[Document]] = {}
    for doc in documents:
        por_hoja.setdefault((doc.source_file, doc.page), []).append(doc)

    for bloque in por_hoja.values():
        if len(bloque) < 2:
            continue
        folios = {doc.folio.value for doc in bloque if not doc.folio.is_empty}
        if len(folios) != 1:
            continue
        folio = folios.pop()
        for doc in bloque:
            if doc.folio.is_empty:
                doc.folio.set(
                    folio, CONF_MEDIA, "", "numero heredado de otra parte de la hoja"
                )



def _attach_payment_voucher(block: Block, documents: list[Document]) -> None:
    """Adjunta un comprobante de tarjeta al ultimo documento de la misma pagina.

    El voucher no aporta datos del titular, pero si confirma el medio de pago y
    el monto efectivamente pagado, por lo que se conserva como dato del
    documento anterior en lugar de generar una ficha independiente.
    """
    if not documents:
        return
    target = documents[-1]
    folded = fold(block.text)
    if "debito" in folded:
        target.medio_pago.set("Tarjeta de debito", CONF_MEDIA, block.lines[0].text)
    elif "credito" in folded:
        target.medio_pago.set("Tarjeta de credito", CONF_MEDIA, block.lines[0].text)
    monto = None
    for line in block.lines:
        if re.search(r"monto venta|^total|\btotal\b", fold(line.text)):
            encontrado = re.search(r"\$\s*([\d.]{3,})", line.text)
            if encontrado:
                monto = parse_clp(encontrado.group(1))
                break
    if monto and target.monto_total.is_empty:
        target.monto_total.set(monto, CONF_MEDIA, "Comprobante de tarjeta adjunto")



def process_folder(
    folder: Path,
    engine: OCREngine | None = None,
    options: PipelineOptions | None = None,
    titulares_config: list[TitularConfig] | None = None,
):
    """Procesa todos los PDF/imagenes de una carpeta y arma el expediente.

    El OCR es la parte lenta, por lo que se ejecuta **una sola vez** por archivo.
    Las recetas manuscritas necesitan conocer antes los nombres del expediente
    para reconstruir el paciente ilegible, asi que esas paginas se reprocesan
    reutilizando el OCR ya calculado (no se vuelve a leer el PDF).
    """
    folder = Path(folder)
    engine = engine or OCREngine()
    options = options or PipelineOptions()
    config = titulares_config or []
    files = sorted(
        p
        for p in folder.iterdir()
        if p.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    )

    # Pasada 1: OCR unico + extraccion, guardando las paginas para reutilizarlas.
    paginas: dict[Path, list[PageOCR]] = {}
    documentos_por_archivo: dict[Path, list[Document]] = {}
    for path in files:
        paginas[path] = ocr_pages(path, engine, dpi=options.dpi, target_height=options.target_height)
        acumulados: list[Document] = []
        for page in paginas[path]:
            acumulados.extend(process_page(path, page, options, None, acumulados))
        documentos_por_archivo[path] = acumulados

    todos = [doc for lista in documentos_por_archivo.values() for doc in lista]
    requiere_pasada_2 = any(
        doc.familia == "receta_manuscrita"
        or (
            doc.familia == "documento_clinico"
            and doc.titular_nombre.is_empty
            and doc.titular_rut.confidence in {CONF_BAJA, CONF_FALTA}
        )
        for doc in todos
    )
    if not requiere_pasada_2:
        generado = datetime.now().strftime("%Y-%m-%d %H:%M")
        expediente = resolve_expediente(
            todos, carpeta=str(folder), generado=generado, config=config
        )
        _completar_desde_config(expediente, config)
        return expediente

    # Nombres de referencia: los declarados en el caso + los leidos en los documentos.
    nombres = [item.nombre for item in config if item.nombre]
    nombres += [d.titular_nombre.value for d in todos if d.titular_nombre.value]

    # Pasada 2: paginas con receta manuscrita o documento clinico con paciente
    # ilegible, reutilizando su OCR.
    for path, lista_paginas in paginas.items():
        necesita_segunda_pasada = {
            doc.page
            for doc in documentos_por_archivo[path]
            if doc.familia == "receta_manuscrita"
            or (
                doc.familia == "documento_clinico"
                and doc.titular_nombre.is_empty
                and doc.titular_rut.confidence in {CONF_BAJA, CONF_FALTA}
            )
        }
        if not necesita_segunda_pasada:
            continue
        nuevos: list[Document] = []
        for page in lista_paginas:
            if page.page not in necesita_segunda_pasada:
                nuevos.extend(
                    doc for doc in documentos_por_archivo[path] if doc.page == page.page
                )
                continue
            nuevos.extend(process_page(path, page, options, nombres, nuevos))
        documentos_por_archivo[path] = nuevos

    documents = [doc for path in files for doc in documentos_por_archivo[path]]
    generado = datetime.now().strftime("%Y-%m-%d %H:%M")
    expediente = resolve_expediente(
        documents, carpeta=str(folder), generado=generado, config=config
    )
    _completar_desde_config(expediente, config)
    return expediente



def _completar_desde_config(expediente, config: list[TitularConfig]) -> None:
    """Rellena el nombre o RUT del titular usando la definicion del caso.

    Nunca sobrescribe un dato leido del documento: solo completa vacios o
    reemplaza nombres truncados por el OCR cuando el RUT coincide exactamente.
    """
    from .normalizers import rut_body

    if not config:
        return
    for doc in expediente.documentos:
        body = rut_body(doc.titular_rut.value if not doc.titular_rut.is_empty else None)
        if not body:
            continue
        for item in config:
            if rut_body(item.rut) != body:
                continue
            if doc.titular_nombre.is_empty:
                doc.titular_nombre.set(
                    item.nombre, CONF_MEDIA, "Nombre tomado de la ficha del titular (caso.json)"
                )
            elif doc.titular_nombre.value.upper() != item.nombre.upper():
                doc.titular_nombre.note = (
                    f"El OCR leyo '{doc.titular_nombre.value}'; la ficha del titular indica "
                    f"'{item.nombre}'"
                )
            break



def save_expediente(expediente, path: Path) -> Path:
    """Guarda el expediente como JSON (insumo del revisor y del Word)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(expediente.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path

