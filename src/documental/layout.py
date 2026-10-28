"""Reconstruccion de lineas y bloques a partir de los tokens de OCR.

Los escaneos de prueba contienen a veces dos documentos en la misma hoja (por
ejemplo dos bonos FONASA apilados). Este modulo agrupa los tokens en lineas y
luego en bloques horizontales, de modo que cada documento se procese por
separado y el recorte de imagen sea el correcto.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .ocr import Token


@dataclass
class Line:
    """Una linea de texto del documento OCR."""

    tokens: list[Token]

    @property
    def text(self) -> str:
        return " ".join(t.text for t in sorted(self.tokens, key=lambda t: t.x0))

    @property
    def x0(self) -> float:
        return min(t.x0 for t in self.tokens)

    @property
    def x1(self) -> float:
        return max(t.x1 for t in self.tokens)

    @property
    def y0(self) -> float:
        return min(t.y0 for t in self.tokens)

    @property
    def y1(self) -> float:
        return max(t.y1 for t in self.tokens)

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def score(self) -> float:
        return max(t.score for t in self.tokens)

    def tokens_from(self, x: float) -> list[Token]:
        """Tokens cuyo centro esta a la derecha de `x` (util para columnas)."""
        return [t for t in sorted(self.tokens, key=lambda t: t.x0) if t.cx >= x]

    def tokens_until(self, x: float) -> list[Token]:
        return [t for t in sorted(self.tokens, key=lambda t: t.x0) if t.cx < x]


@dataclass
class Block:
    """Conjunto de lineas que forman un documento dentro de la pagina."""

    lines: list[Line] = field(default_factory=list)

    @property
    def y0(self) -> float:
        return min(line.y0 for line in self.lines)

    @property
    def y1(self) -> float:
        return max(line.y1 for line in self.lines)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


def build_lines(tokens: list[Token], *, y_tolerance_ratio: float = 0.55) -> list[Line]:
    """Agrupa tokens en lineas comparando el centro vertical.

    La tolerancia se calcula por altura de token para tolerar documentos
    torcidos o con distintas tipografias en la misma fila.
    """
    if not tokens:
        return []
    ordered = sorted(tokens, key=lambda t: (t.cy, t.x0))
    lines: list[list[Token]] = []
    for token in ordered:
        placed = False
        for group in lines:
            ref = group[-1]
            tolerance = max(4.0, y_tolerance_ratio * max(ref.height, token.height))
            if abs(token.cy - ref.cy) <= tolerance:
                group.append(token)
                placed = True
                break
        if not placed:
            lines.append([token])
    return [Line(tokens=sorted(group, key=lambda t: t.x0)) for group in lines]


def split_blocks(
    lines: list[Line],
    *,
    page_height: int,
    gap_ratio: float = 0.035,
    markers: tuple[str, ...] = (),
) -> list[Block]:
    """Divide las lineas en bloques (documentos) usando huecos verticales.

    Un bloque nuevo comienza cuando:
      - hay un hueco vertical grande entre lineas (seccion en blanco), o
      - una linea contiene un marcador de inicio de documento (p. ej.
        "BONO DE ATENCION AMBULATORIA") y ya hay contenido en el bloque actual.
    """
    if not lines:
        return []
    lines = sorted(lines, key=lambda line: line.cy)
    min_gap = page_height * gap_ratio
    blocks: list[Block] = [Block(lines=[lines[0]])]
    for previous, current in zip(lines, lines[1:]):
        gap = current.y0 - previous.y1
        starts_new = gap > min_gap
        if not starts_new and markers:
            text = current.text.upper()
            starts_new = any(marker.upper() in text for marker in markers)
        if starts_new:
            blocks.append(Block(lines=[current]))
        else:
            blocks[-1].lines.append(current)
    return [block for block in blocks if block.lines]


def line_value_after(line: Line, label: str, *, x_min: float = 0.0) -> str:
    """Devuelve el texto de una linea que sigue a una etiqueta.

    Se usa para campos del tipo "Fecha Emision : 29-09-2026", donde la etiqueta y
    el valor estan en la misma linea.
    """
    from .normalizers import fold

    text = line.text
    folded = fold(text)
    label_folded = fold(label)
    index = folded.find(label_folded)
    if index < 0:
        return ""
    # Se recorta sobre el texto original usando la proporcion del indice.
    original_index = _map_fold_index(text, index)
    remainder = text[original_index + len(label):]
    return remainder.lstrip(" :.-")


def _map_fold_index(text: str, folded_index: int) -> int:
    """Aproxima el indice en el texto original de un indice del texto plegado."""
    from .normalizers import fold

    for i in range(len(text) + 1):
        if len(fold(text[:i])) >= folded_index:
            return i
    return 0
