# Aviso legal

## No es asesoría jurídica

Esta herramienta es un **programa de apoyo documental**. No entrega asesoría
jurídica, no interpreta la ley y no reemplaza el análisis, la estrategia ni la
revisión de una abogada o abogado.

## El OCR puede equivocarse

El reconocimiento óptico de caracteres (OCR) es una estimación: puede confundir
números, nombres, fechas y montos, especialmente en documentos torcidos,
borrosos, manuscritos o con sellos.

Por eso la herramienta:

- marca cada dato con un nivel de confianza;
- genera un **revisor** para corregir;
- deja un **informe** que debe contrastarse con el documento original.

**La revisión humana es obligatoria** antes de usar cualquier dato en un escrito,
una presentación judicial o una gestión administrativa.

## Sin garantías

El software se entrega **“tal cual”**, sin garantía de exactitud, disponibilidad
o aptitud para un fin determinado. En la medida permitida por la ley, el autor no
responde por daños derivados del uso de la herramienta o de errores del OCR.

## Responsabilidad profesional

El uso de los resultados y su incorporación a un expediente son responsabilidad
de quien ejerce la profesión. Verifica siempre los datos críticos (ROL, tribunal,
partes, fechas y montos) contra los documentos originales.

## Licencia

El uso del software se rige por la **PolyForm Internal Use License 1.0.0**
(ver [`LICENSE`](LICENSE)): uso interno gratuito; prohibida la distribución y la
incorporación en productos o servicios ofrecidos a terceros.

## Componentes de terceros

La herramienta usa bibliotecas de código abierto, cada una con su propia
licencia: **RapidOCR 3.10.0** (Apache-2.0), modelos **PP-OCRv6 small** de
PaddleOCR convertidos a ONNX, **ONNX Runtime 1.31.0** (MIT), **PyMuPDF 2.0**
(AGPL-3.0 o licencia comercial), **Pillow 13.0.0** (MIT-CMU) y **python-docx
1.2.0** (MIT). Los modelos de OCR se distribuyen dentro del paquete RapidOCR y
no se descargan de internet.

Versiones, enlaces y advertencia sobre la licencia de PyMuPDF:
[`TERCEROS.md`](TERCEROS.md).

El OCR corre **100 % local**: no se usa Tesseract ni ningún servicio en la nube.
