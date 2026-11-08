"""OCR local sobre PDF (o imagenes) usando RapidOCR + ONNX Runtime.

No se usa Tesseract ni ningun servicio en la nube: todo corre en el equipo del
estudio. Cada token conserva su caja (x0, y0, x1, y1) y su confianza, lo que
permite reconstruir lineas, columnas y detectar dos documentos en una hoja.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image

# Rango de escala usado al preprocesar: los escaneos de prueba son de ~1024 px
# de alto, insuficientes para letra pequena. Se reescala a un alto objetivo.
TARGET_HEIGHT = 2200
MAX_SCALE = 3.0

# Tope de pixeles al rasterizar una pagina o cargar una imagen. Algunos PDF
# (p. ej. topografias con pagina gigante) a 250-300 dpi generarian imagenes de
# 100+ millones de pixeles, que agotan la memoria y hacen el OCR eterno. Se baja
# el dpi efectivo para no pasar de este presupuesto.
MAX_PIXELS = 24_000_000


@dataclass
class Token:
    """Una palabra o frase reconocida por el OCR."""

    text: str
    box: tuple[float, float, float, float]
    score: float

    @property
    def x0(self) -> float:
        return self.box[0]

    @property
    def y0(self) -> float:
        return self.box[1]

    @property
    def x1(self) -> float:
        return self.box[2]

    @property
    def y1(self) -> float:
        return self.box[3]

    @property
    def cx(self) -> float:
        return (self.box[0] + self.box[2]) / 2

    @property
    def cy(self) -> float:
        return (self.box[1] + self.box[3]) / 2

    @property
    def height(self) -> float:
        return self.box[3] - self.box[1]

    def to_dict(self) -> dict:
        return {"text": self.text, "box": list(self.box), "score": round(self.score, 4)}


@dataclass
class PageOCR:
    """Resultado del OCR de una pagina."""

    page: int
    width: int
    height: int
    tokens: list[Token]
    image: Image.Image

    @property
    def text(self) -> str:
        return "\n".join(t.text for t in self.tokens)


class OCREngine:
    """Envoltura de RapidOCR con carga diferida (el modelo tarda ~1 s)."""

    def __init__(self) -> None:
        self._engine = None

    def _load(self):
        if self._engine is None:
            from rapidocr import RapidOCR

            self._engine = RapidOCR()
        return self._engine

    def run(self, image: Image.Image) -> list[Token]:
        engine = self._load()
        # RapidOCR espera BGR (convencion OpenCV).
        array = np.array(image.convert("RGB"))[:, :, ::-1].copy()
        result = engine(array)
        tokens: list[Token] = []
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return tokens
        texts = result.txts or []
        scores = result.scores or []
        for box, text, score in zip(boxes, texts, scores):
            x_coords = [float(p[0]) for p in box]
            y_coords = [float(p[1]) for p in box]
            clean = (text or "").strip()
            if not clean:
                continue
            tokens.append(
                Token(
                    text=clean,
                    box=(min(x_coords), min(y_coords), max(x_coords), max(y_coords)),
                    score=float(score),
                )
            )
        return tokens


def render_pdf(path: Path, dpi: int = 300, max_pixels: int = MAX_PIXELS) -> list[Image.Image]:
    """Renderiza cada pagina del PDF como imagen RGB a la resolucion indicada.

    Si una pagina es tan grande que a ``dpi`` superaria ``max_pixels``, se baja
    el dpi efectivo solo para esa pagina (evita imagenes gigantes y lentitud).
    """
    pages: list[Image.Image] = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            ancho_pt, alto_pt = page.rect.width, page.rect.height
            dpi_efectivo = dpi
            if ancho_pt > 0 and alto_pt > 0:
                escala = dpi / 72.0
                pixeles = (ancho_pt * escala) * (alto_pt * escala)
                if pixeles > max_pixels:
                    dpi_efectivo = int(max(72, dpi * math.sqrt(max_pixels / pixeles)))
            pixmap = page.get_pixmap(dpi=dpi_efectivo, colorspace=pymupdf.csRGB)
            image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
            pages.append(image)
    return pages


def load_image(path: Path, max_pixels: int = MAX_PIXELS) -> list[Image.Image]:
    """Carga un archivo de imagen suelto (JPG/PNG/TIFF) como una pagina.

    Si la imagen supera ``max_pixels`` se reduce (evita fotos gigantes).
    """
    with Image.open(path) as image:
        imagen = image.convert("RGB")
    ancho, alto = imagen.size
    if ancho * alto > max_pixels:
        factor = math.sqrt(max_pixels / (ancho * alto))
        imagen = imagen.resize(
            (max(1, int(ancho * factor)), max(1, int(alto * factor))), Image.LANCZOS
        )
    return [imagen]


def preprocess(image: Image.Image, *, target_height: int = TARGET_HEIGHT) -> Image.Image:
    """Mejora la imagen antes del OCR.

    - Lleva la imagen a un alto objetivo: agranda los escaneos de baja
      resolucion (mejora la letra pequena) y reduce las fotos de celular de
      ~12 MP. La reduccion no mejora la lectura (RapidOCR ya normaliza el
      tamano internamente) y apenas gana velocidad: medido sobre fotos de
      2779 x 3549 px dio 28,5 s frente a 31,2 s, con texto extraido identico.
      Se mantiene porque acota el uso de memoria y evita trabajar de mas.
    - Aplica autocontraste en escala de grises para separar tinta de papel.
    - Mantiene modo RGB porque RapidOCR espera 3 canales.
    """
    width, height = image.size
    scale = min(MAX_SCALE, target_height / max(height, 1))
    if abs(scale - 1.0) > 0.01:
        nuevo = (max(1, int(width * scale)), max(1, int(height * scale)))
        image = image.resize(nuevo, Image.LANCZOS)
    gray = image.convert("L")
    # Autocontraste suave: recorta el 1 % de los extremos del histograma.
    hist = gray.histogram()
    total = sum(hist)
    cutoff = int(total * 0.01)
    low, acc = 0, 0
    for value, count in enumerate(hist):
        acc += count
        if acc > cutoff:
            low = value
            break
    acc = 0
    high = 255
    for value in range(255, -1, -1):
        acc += hist[value]
        if acc > cutoff:
            high = value
            break
    if high <= low:
        high = min(255, low + 1)
    stretch = gray.point(lambda p: max(0, min(255, int((p - low) * 255 / (high - low)))))
    return stretch.convert("RGB")


def ocr_pages(
    path: Path,
    engine: OCREngine | None = None,
    dpi: int = 300,
    target_height: int = TARGET_HEIGHT,
) -> list[PageOCR]:
    """Ejecuta el pipeline completo sobre un archivo PDF o imagen."""
    engine = engine or OCREngine()
    suffix = path.suffix.lower()
    raw_pages = (
        load_image(path)
        if suffix in {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
        else render_pdf(path, dpi=dpi)
    )

    results: list[PageOCR] = []
    for index, raw in enumerate(raw_pages, start=1):
        processed = preprocess(raw, target_height=target_height)
        tokens = engine.run(processed)
        results.append(
            PageOCR(
                page=index,
                width=processed.width,
                height=processed.height,
                tokens=tokens,
                image=processed,
            )
        )
    return results
