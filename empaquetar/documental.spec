# -*- mode: python ; coding: utf-8 -*-
"""Empaqueta la mini app como carpeta ejecutable (onedir) con PyInstaller.

Uso (desde la raiz del proyecto):

    pyinstaller --noconfirm --clean empaquetar/documental.spec

El resultado queda en ``dist/LectorDeDocumentos/`` y se distribuye como ZIP:
el usuario descomprime y hace doble clic en ``Lector de documentos.exe``.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

RAIZ = Path(SPECPATH).resolve().parent
SRC = RAIZ / "src"

datas = [(str(SRC / "documental" / "revisor_template.html"), "documental")]
binaries = []
hiddenimports = [
    "documental",
    "documental.cli",
    "documental.gui",
    "pymupdf",
    "fitz",
    "docx",
    "PIL.Image",
    "numpy",
]

# Solo estos paquetes necesitan datos/binarios propios (modelos ONNX y librerias).
# El resto lo resuelven los hooks de PyInstaller.
for paquete in ("rapidocr", "onnxruntime"):
    datos_paquete, binarios_paquete, ocultos = collect_all(paquete)
    datas += datos_paquete
    binaries += binarios_paquete
    hiddenimports += ocultos

a = Analysis(
    [str(RAIZ / "empaquetar" / "entrada.py")],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pytest",
        "pymupdf4llm",
        "pymupdf_layout",
        "numpy.typing.tests",
        "tkinter.test",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Lector de documentos",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="LectorDeDocumentos",
)
