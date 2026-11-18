# Componentes de terceros y motor de OCR

Este documento declara qué motor de OCR usa la herramienta, su versión, su
licencia y la fuente original. Las versiones coinciden con `requirements.txt` y
`pyproject.toml`.

## Motor de OCR

| Componente | Versión | Función | Licencia | Fuente |
|---|---|---|---|---|
| **RapidOCR** | 3.10.0 | Detección y reconocimiento de texto (motor principal) | Apache-2.0 | https://github.com/RapidAI/RapidOCR |
| **Modelos PP-OCRv6 small (ONNX)** | incluidos en el paquete RapidOCR | Pesos de detección y reconocimiento en español/inglés | Apache-2.0 (verificar en el paquete instalado) | https://github.com/PaddlePaddle/PaddleOCR |
| **ONNX Runtime** | 1.31.0 | Ejecución local de los modelos ONNX | MIT | https://github.com/microsoft/onnxruntime |
| **PyMuPDF (fitz)** | 2.0 | Lectura de PDF, render de páginas y extracción de texto | AGPL-3.0 o licencia comercial | https://github.com/pymupdf/PyMuPDF |
| **Pillow** | 13.0.0 | Preprocesado de imágenes (contraste, escala) | MIT-CMU | https://github.com/python-pillow/Pillow |
| **NumPy** | (dependencia de RapidOCR) | Operaciones numéricas | BSD-3-Clause | https://github.com/numpy/numpy |
| **python-docx** | 1.2.0 | Generación del informe Word | MIT | https://github.com/python-openxml/python-docx |

## Cómo se usa el OCR

1. **PyMuPDF** abre el PDF y renderiza cada página a imagen (o lee su capa de
   texto si ya existe).
2. **Pillow** normaliza el contraste y el tamaño de la imagen.
3. **RapidOCR** ejecuta los modelos **PP-OCRv6 small** convertidos a **ONNX**
   mediante **ONNX Runtime**, en el mismo computador.
4. Cada palabra conserva su caja (x0, y0, x1, y1) y su confianza, lo que permite
   reconstruir líneas, columnas y detectar dos documentos en una misma hoja.

**No se usa Tesseract, no se llama a ninguna API y ninguna imagen ni texto sale
del equipo.** La primera ejecución no descarga modelos: vienen incluidos en el
paquete `rapidocr`.

## Licencia de PyMuPDF

PyMuPDF se distribuye bajo **AGPL-3.0** o licencia comercial. Si este programa se
entrega como binario cerrado o se ofrece como servicio en red, la AGPL exige
poner a disposición el código fuente correspondiente o contar con una licencia
comercial de Artifex. Este repositorio se distribuye con su código fuente, pero
conviene revisar el caso concreto con quien gestione la licencia del producto.

## Verificación de versiones

Para confirmar las versiones instaladas en un equipo:

```bash
python -m pip show rapidocr onnxruntime pymupdf pillow python-docx
```

Para revisar la licencia declarada por cada paquete:

```bash
python -m pip show rapidocr | grep -i license
```
