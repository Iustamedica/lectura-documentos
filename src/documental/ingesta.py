"""Preparacion de fotos e imagenes: JPG -> PDF antes del OCR.

Una foto de celular no se puede meter en un A4 fijo: una imagen de 2900 x 3800
px reducida a una hoja A4 pierde resolucion antes de que el OCR la vea. Por eso
el tamano de pagina se calcula desde los pixeles a 300 dpi, de modo que al
volver a renderizar el PDF (`--dpi 300`) se recupere exactamente la imagen
original, sin perdida.

Ademas agrupa las fotos capturadas con pocos segundos de diferencia: en la
practica suelen ser las hojas del mismo documento (un contrato fotografiado
pagina por pagina). La agrupacion es una propuesta, no una certeza, y queda
registrada en el mapa para poder revisarla.

Los archivos originales nunca se modifican ni se mueven.
"""

from __future__ import annotations

import csv
import io
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

# Extensiones tratadas como fotografia o imagen escaneada.
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}

# 1 pulgada = 72 puntos. Se asume 300 dpi para convertir pixeles a puntos,
# que es el mismo valor por defecto de `--dpi` en el pipeline.
DPI_CONVERSION = 300

# Etiqueta EXIF de orientacion (0 o 1 significan "sin rotacion pendiente").
EXIF_ORIENTACION = 274

# Nombre de camara con marca de tiempo: IMG_20261102_145929.jpg
_TIEMPO_EN_NOMBRE = re.compile(r"(?<!\d)(\d{8})[_-]?(\d{6})(?!\d)")


def marca_de_tiempo(ruta: Path) -> datetime | None:
    """Momento de captura de una imagen.

    Se intenta, en orden: la marca de tiempo del nombre del archivo
    (``IMG_20261102_145929.jpg``), la fecha EXIF de la camara y, como ultimo
    recurso, la fecha de modificacion del archivo.
    """
    ruta = Path(ruta)
    match = _TIEMPO_EN_NOMBRE.search(ruta.stem)
    if match:
        try:
            return datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
        except ValueError:
            pass
    try:
        with Image.open(ruta) as image:
            exif = image.getexif()
            # 36867 = DateTimeOriginal, 306 = DateTime
            valor = exif.get(36867) or exif.get(306)
        if valor:
            return datetime.strptime(str(valor).strip(), "%Y:%m:%d %H:%M:%S")
    except (OSError, ValueError):
        pass
    try:
        return datetime.fromtimestamp(ruta.stat().st_mtime)
    except OSError:
        return None


def _agregar_imagen(doc: pymupdf.Document, ruta: Path, dpi: int) -> None:
    """Agrega una imagen como pagina nueva, sin reducir su resolucion."""
    with Image.open(ruta) as image:
        orientacion = image.getexif().get(EXIF_ORIENTACION, 1)
        if orientacion in (0, 1, None):
            ancho, alto = image.size
            pagina = doc.new_page(width=ancho * 72.0 / dpi, height=alto * 72.0 / dpi)
            pagina.insert_image(pagina.rect, filename=str(ruta))
            return
        # Quedaba una rotacion pendiente: se aplica y se guarda sin perdida.
        girada = ImageOps.exif_transpose(image)
        ancho, alto = girada.size
        buffer = io.BytesIO()
        girada.save(buffer, format="PNG", optimize=True)
    pagina = doc.new_page(width=ancho * 72.0 / dpi, height=alto * 72.0 / dpi)
    pagina.insert_image(pagina.rect, stream=buffer.getvalue())


def imagen_a_pdf(
    rutas: list[Path], destino: Path, *, dpi: int = DPI_CONVERSION
) -> Path:
    """Convierte una o varias imagenes en un PDF (una pagina por imagen)."""
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    try:
        for ruta in rutas:
            _agregar_imagen(doc, Path(ruta), dpi)
        doc.save(str(destino), garbage=3, deflate=True)
    finally:
        doc.close()
    return destino


def agrupar_por_tiempo(
    items: list[tuple[Path, datetime | None]], max_segundos: int
) -> list[list[Path]]:
    """Agrupa archivos consecutivos capturados con pocos segundos de diferencia.

    ``items`` ya debe venir ordenado por momento de captura. Un archivo sin
    momento conocido nunca se agrupa con otro, para no inventar relaciones.
    """
    if max_segundos <= 0:
        return [[ruta] for ruta, _ in items]
    grupos: list[list[Path]] = []
    ultimo: datetime | None = None
    for ruta, momento in items:
        if grupos and momento is not None and ultimo is not None:
            diferencia = (momento - ultimo).total_seconds()
            if 0 <= diferencia <= max_segundos:
                grupos[-1].append(ruta)
                ultimo = momento
                continue
        grupos.append([ruta])
        ultimo = momento
    return grupos


@dataclass
class ResultadoPreparacion:
    """Lo que hizo (o haria, en modo simulacion) la preparacion de la carpeta."""

    destino: Path
    grupos: list[list[Path]] = field(default_factory=list)
    pdf_por_imagen: dict[Path, Path] = field(default_factory=dict)
    pdfs_copiados: list[tuple[Path, Path]] = field(default_factory=list)
    mapa: list[dict[str, str]] = field(default_factory=list)
    dry_run: bool = False

    @property
    def total_imagenes(self) -> int:
        return sum(len(grupo) for grupo in self.grupos)

    @property
    def total_pdfs(self) -> int:
        return len(self.grupos) + len(self.pdfs_copiados)

    def escribir_mapa(self, path: Path) -> Path:
        """Escribe el CSV de trazabilidad imagen -> PDF -> grupo.

        Se usa punto y coma como separador y BOM de UTF-8 para que Excel en
        espanol lo abra en columnas sin pasos adicionales.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(
                archivo,
                fieldnames=["orden", "grupo", "imagen_original", "momento", "pdf", "estado"],
                delimiter=";",
            )
            escritor.writeheader()
            escritor.writerows(self.mapa)
        return path


def _nombre_pdf(grupo: list[Path]) -> str:
    """Nombre del PDF generado a partir de un grupo de imagenes."""
    if len(grupo) == 1:
        return grupo[0].with_suffix(".pdf").name
    return f"{grupo[0].stem}__{len(grupo)}pag.pdf"


def preparar(
    origen: Path,
    destino: Path,
    *,
    unir_por_tiempo: int = 0,
    dpi: int = DPI_CONVERSION,
    copiar_pdf: bool = True,
    dry_run: bool = False,
    forzar: bool = False,
) -> ResultadoPreparacion:
    """Convierte las imagenes de ``origen`` en PDF dentro de ``destino``.

    ``unir_por_tiempo`` son los segundos maximos entre dos fotos para
    considerarlas hojas del mismo documento (0 desactiva la agrupacion).

    En ``dry_run`` no se escribe ningun archivo: solo se calcula el plan y el
    mapa, para revisarlo antes de tocar nada.
    """
    origen = Path(origen)
    destino = Path(destino)
    if not origen.is_dir():
        raise NotADirectoryError(f"No existe la carpeta de origen: {origen}")
    if destino.exists() and any(destino.iterdir()) and not (forzar or dry_run):
        raise FileExistsError(
            f"La carpeta destino ya tiene archivos: {destino}. "
            "Use otra carpeta o --forzar para mezclar resultados."
        )

    archivos = sorted(p for p in origen.iterdir() if p.is_file())
    imagenes = [p for p in archivos if p.suffix.lower() in IMAGE_SUFFIXES]
    pdfs = [p for p in archivos if p.suffix.lower() == ".pdf"]

    items = [(p, marca_de_tiempo(p)) for p in imagenes]
    if unir_por_tiempo > 0:
        items.sort(key=lambda par: (par[1] is None, par[1] or datetime.min, par[0].name))
        grupos = agrupar_por_tiempo(items, unir_por_tiempo)
    else:
        grupos = [[p] for p in imagenes]

    resultado = ResultadoPreparacion(destino=destino, grupos=grupos, dry_run=dry_run)
    momentos = {ruta: momento for ruta, momento in items}

    if not dry_run:
        destino.mkdir(parents=True, exist_ok=True)

    orden = 0
    for numero_grupo, grupo in enumerate(grupos, start=1):
        pdf_destino = destino / _nombre_pdf(grupo)
        if not dry_run:
            imagen_a_pdf(grupo, pdf_destino, dpi=dpi)
        for ruta in grupo:
            orden += 1
            resultado.pdf_por_imagen[ruta] = pdf_destino
            momento = momentos.get(ruta)
            resultado.mapa.append(
                {
                    "orden": str(orden),
                    "grupo": str(numero_grupo),
                    "imagen_original": ruta.name,
                    "momento": momento.strftime("%Y-%m-%d %H:%M:%S") if momento else "",
                    "pdf": pdf_destino.name,
                    "estado": "unica" if len(grupo) == 1 else f"{len(grupo)} paginas",
                }
            )

    if copiar_pdf:
        for ruta in pdfs:
            pdf_destino = destino / ruta.name
            if not dry_run:
                shutil.copy2(ruta, pdf_destino)
            resultado.pdfs_copiados.append((ruta, pdf_destino))
            orden += 1
            resultado.mapa.append(
                {
                    "orden": str(orden),
                    "grupo": "",
                    "imagen_original": ruta.name,
                    "momento": "",
                    "pdf": pdf_destino.name,
                    "estado": "pdf copiado",
                }
            )

    return resultado
