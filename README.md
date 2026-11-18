# Lector de documentos legales (OCR local)

**Convierte fotos y PDF en un borrador editable y un informe Word, en tu propio computador y sin subir nada a internet.**

Pensado para abogados y equipos jurídicos. Tiene cuatro modalidades: **judicial** (expedientes y prueba), **doctrina** (libros, artículos y tesis), **jurisprudencia** (sentencias) y **actos administrativos** (resoluciones y dictámenes). Extrae los datos de identificación de cada documento y deja una **primera versión que se revisa y se corrige** en un HTML que se abre en el navegador, más un **informe en Word**. Todo corre **local**.

> ⚖️ **La herramienta asiste, no reemplaza la revisión del abogado.** Revise siempre el borrador y el informe antes de usarlos.

## Qué hace
- Lee **fotos (JPG/PNG) y PDF** de una carpeta.
- **Clasifica** cada documento según la modalidad elegida: judicial (escritos, resoluciones, notificaciones, contratos, comprobantes, poderes, informes), doctrina, jurisprudencia o acto administrativo.
- **Extrae** los datos propios: ROL/RIT, tribunal, carátula, partes, fechas, folios, notaría, abogados y montos; o autores, año, DOI e ISBN en doctrina; o institución, número y materia en actos administrativos.
- Genera:
  - **`Revision.html`** — borrador editable para revisar y corregir.
  - **`Informe.docx`** — informe en Word con portada, resumen por categoría, índice y fichas por documento.
  - (opcional) **PDFs ordenados por fuente y categoría**, índice y comprimidos para el Poder Judicial.

## Cómo se usa

1. Descarga el paquete de la última versión publicada:
   - **Windows:** [LectorDeDocumentos-windows.zip](https://github.com/Iustamedica/lectura-documentos/releases/latest/download/LectorDeDocumentos-windows.zip)
   - **Linux:** [LectorDeDocumentos-linux.zip](https://github.com/Iustamedica/lectura-documentos/releases/latest/download/LectorDeDocumentos-linux.zip)
2. Descomprime el ZIP en una carpeta (por ejemplo, el Escritorio).
3. Doble clic en **`Lector de documentos`** (o `Lector de documentos.exe`).
4. Elige la carpeta de trabajo, marca la **modalidad** (judicial, doctrina, jurisprudencia o actos administrativos) y presiona **Procesar documentos**.
5. Al terminar, abre **`Resultados/Revision.html`** para revisar y corregir los datos.

La primera vez puede tardar unos segundos en abrir; después funciona sin conexión.
El paquete pesa alrededor de 200 MB (incluye el motor de OCR y sus modelos).

Se puede instalar también desde el terminal conforme a las instrucciones más abajo.

> **Aviso de Windows:** el programa no está firmado digitalmente. Si aparece
> "Windows protegió tu PC", haz clic en **Más información → Ejecutar de todas
> formas**. Es normal en programas sin firma comercial. Algunos antivirus
> pueden marcarlo como sospechoso (falso positivo de los empaquetados).

El programa trabaja **dentro de la carpeta que eliges**: ahí crea `1. Documentos a procesar/` y `Resultados/` (con el HTML, el JSON, el Word y, si corresponde, los PDF ordenados). Tus archivos originales **no se mueven ni se borran**.

## Instalación por terminal y código (opcional, para personas más técnicas)

**1) Instalar (una sola vez)**
- **Windows:** doble clic en `instalar.bat`.
- **Linux/Mac:** doble clic en `instalar.sh` (o `bash instalar.sh`).

**2) Usar**
1. Abre la carpeta **`Expediente`** (se crea sola).
2. Copia tus **fotos y PDF** en **`Expediente/1. Documentos a procesar`**.
3. Doble clic en **`Procesar documentos`** (o en `Lector de documentos` para la aplicación).
4. Revisa **`Expediente/Resultados/Revision.html`** y **`Informe.docx`**.

📘 Catálogo, campos y límites del modo judicial: **[PERFIL-LEGAL.md](PERFIL-LEGAL.md)**.

## Qué genera
| Archivo | Para qué |
|---|---|
| `Resultados/Revision.html` | Abrir en el navegador para **revisar y corregir** los datos. |
| `Resultados/Informe.docx` | El **informe Word** (portada con ROL y carátula). |
| `Resultados/Documentos/` | PDFs **ordenados por fuente y categoría** e índices (si usas comprimir/ordenar). |
| `Resultados/expediente.json` | Datos crudos (soporte técnico). |
| `Resultados/Registro.txt` | Resumen del proceso (útil si algo falla). |

## Documentación

| Documento | Contenido |
|---|---|
| [GUIA-USO-LEGAL.md](GUIA-USO-LEGAL.md) | Guía paso a paso para abogados. |
| [FAQ.md](FAQ.md) | Avisos de Windows, antivirus, tamaños y problemas frecuentes. |
| [PERFIL-LEGAL.md](PERFIL-LEGAL.md) | Categorías, tipos de documento y campos del modo judicial. |
| [PRIVACIDAD.md](PRIVACIDAD.md) | Cómo se tratan los datos del expediente. |
| [AVISO-LEGAL.md](AVISO-LEGAL.md) | Alcance, límites del OCR y responsabilidad. |
| [CHANGELOG.md](CHANGELOG.md) | Historial de versiones. |
| [SECURITY.md](SECURITY.md) | Cómo reportar vulnerabilidades. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Cómo colaborar con el proyecto. |
| [DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md) | Arquitectura, perfiles y empaquetado (para informática). |
| [TERCEROS.md](TERCEROS.md) | Motor de OCR, versiones, licencias y fuentes. |

## Modalidades

Al abrir la aplicación eliges **qué tipo de documentos** vas a procesar. También puedes fijarla con `--perfil` o dejarla escrita en un archivo `perfil.txt` dentro de la carpeta.

| Modalidad | Para qué | Carpetas de salida |
|---|---|---|
| **Judicial** | Escritos, resoluciones, notificaciones, contratos, boletas, garantías y cheques. | `01-expedientes/…`, `05-documentos/…` |
| **Doctrina** | Libros, artículos, tesis y papers. **Un PDF = un ítem.** | `01-libros`, `02-articulos`, `03-tesis`, `04-papers`, `05-otros` |
| **Jurisprudencia** | Sentencias de la Corte Suprema, Cortes de Apelaciones y Tribunal Constitucional. **Un PDF = un fallo.** | `01-corte-suprema`, `02-corte-apelaciones`, `03-tribunal-constitucional`, `04-tribunales-especiales`, `05-otros` |
| **Actos administrativos** | Resoluciones, dictámenes y oficios de Contraloría, Superintendencias, ministerios y municipalidades. **Un PDF = un acto.** | `01-contraloria`, `02-superintendencia-salud`, `03-ministerios`, `04-municipalidades`, `05-otros` |

- La carpeta también ayuda: si se llama `Doctrina`, `Jurisprudencia`, `Actos administrativos` o `Expediente`, la modalidad se preselecciona sola.
- En **judicial**, si aparecen documentos de doctrina o jurisprudencia, puedes elegir si se guardan en **carpetas propias** o **junto al resto** de los documentos.
- Doctrina, jurisprudencia y actos conservan **un PDF = un documento**: no se dividen por páginas. Si un escaneo no trae capa de texto, se OCR-ean solo las primeras páginas para leer los datos de identificación.
- La modalidad de doctrina extrae **título, autores, año, editorial o revista, DOI, ISBN, idioma y páginas**. Para el catálogo completo: `documental biblioteca "Mi biblioteca" --catalogo catalogo.csv`.

```bash
documental procesar "Mi carpeta" --perfil doctrina
documental jurisprudencia --carpeta "Mis sentencias"
documental actos --carpeta "Actos administrativos"
```

## Motor de OCR y fuentes

El OCR corre **100 % local**: **RapidOCR 3.10.0** (modelos PP-OCRv6 en formato ONNX) sobre **ONNX Runtime 1.31.0**, con las páginas renderizadas por **PyMuPDF 2.0**. No se usa Tesseract ni servicios en la nube; ninguna imagen sale del equipo.

Versiones exactas, licencias y enlaces de cada componente: **[TERCEROS.md](TERCEROS.md)**.

## Advertencias de calidad y tamaño
- **Orientación:** documentos derechos y en la **misma orientación** (mejor lectura).
- **Escrito a mano:** baja precisión; debe **revisarse especialmente**.
- **Peso (Poder Judicial):** límite **10 MB por archivo / 30 MB total**; la herramienta avisa y hay una opción que comprime los PDF.

## Privacidad
- **Todo el procesamiento es local**; no se envía nada a internet.
- El repositorio contiene **solo el programa**: los expedientes (nombres, RUT, datos del caso) **nunca** se suben. Detalles en [PRIVACIDAD.md](PRIVACIDAD.md).

## Créditos y licencia

Desarrollado en colaboración con **DeepSeek V4.1** (asistencia de IA en mejoras al diseño, implementación y pruebas). La validación de los documentos y el criterio jurídico son **siempre** del equipo legal.

### Licencia

**PolyForm Internal Use License 1.0.0** — texto completo en [LICENSE](LICENSE).

Qué permite la licencia:

- ✅ **Puedes usar la herramienta gratis dentro de tu estudio u oficina**, incluso para atender tus casos.
- ✅ **Puedes modificarla** para uso interno.
- ❌ **No puedes distribuirla, revenderla ni integrarla en un producto o servicio que ofrezcas a terceros.**

Para distribuir el software o acordar otro tipo de licencia, contacta al autor del proyecto.

> Esta es una licencia *source-available* (código disponible), no una licencia de código abierto aprobada por OSI.

## Contacto

- **Dudas, errores o mejoras:** abre un *issue* en el repositorio.
- **Licencias comerciales, distribución o adaptaciones:** abre un *issue* con el
  título “Licencia comercial” o escribe a: contacto@iustamedica.cl

## Para desarrolladores
Visión general (arquitectura, perfiles, estructura, pruebas y empaquetado): **[DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md)**.
Detalle del motor de OCR y de las modalidades: **[DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md)**.
Perfil judicial: **[PERFIL-LEGAL.md](PERFIL-LEGAL.md)**.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m documental.cli --help
```

Comandos: `expediente`, `procesar`, `doctrina`, `jurisprudencia`, `actos`, `clasificar`, `preparar`, `revisor`, `informe`, `ordenar`, `compilar`.
Requiere Python 3.10+.

Modalidad por defecto: **judicial**. Las demás: `--perfil doctrina|jurisprudencia|administrativo`, `DOCUMENTAL_PERFIL=...` o `perfil.txt`.

```bash
# Inventario rápido de una carpeta judicial, sin OCR
PYTHONPATH=src .venv/bin/python -m documental.cli clasificar "expediente/" --csv inventario.csv

# Proceso completo del expediente judicial
PYTHONPATH=src .venv/bin/python -m documental.cli expediente --ordenar

# Una biblioteca de doctrina (un PDF = un item)
PYTHONPATH=src .venv/bin/python -m documental.cli doctrina --carpeta "Mi biblioteca" --ordenar
```

### Generar el ejecutable (sin terminal para el usuario final)

En Linux, la app necesita Tkinter (`sudo apt install python3-tk`). En Windows
viene incluido con Python.

```bash
# Linux
bash empaquetar/empaquetar_linux.sh

# Windows (en un equipo Windows)
empaquetar\empaquetar_windows.bat
```

El resultado queda en `dist/LectorDeDocumentos/`. Al publicar un tag (`v*`), el
workflow `.github/workflows/empaquetar.yml` genera los ZIP de Windows y Linux y
los adjunta a la Release; ese enlace es el que se comparte con los abogados:

```
https://github.com/Iustamedica/lectura-documentos/releases/latest/download/LectorDeDocumentos-windows.zip
```
