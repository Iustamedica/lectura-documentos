"""Extraccion local de datos desde documentos escaneados.

Uso tipico desde la linea de comandos (ver `cli.py`):

    documental procesar  ../../escaneos-csm --json salidas/expediente.json
    documental revisor   salidas/expediente.json --html salidas/revision.html
    documental informe   salidas/expediente.json --docx salidas/informe.docx
"""

__version__ = "0.1.0"

__all__ = [
    "classify",
    "layout",
    "models",
    "normalizers",
    "ocr",
    "pipeline",
    "titulares",
]
