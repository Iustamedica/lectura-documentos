# Lector de documentos para expedientes judiciales (OCR local)

**Convierte fotos y PDF de un expediente en un borrador editable y un informe Word, en tu propio computador y sin subir nada a internet.**

Pensado para abogados y equipos jurídicos: lee los documentos de un expediente (escritos, resoluciones, notificaciones, contratos, comprobantes, poderes, certificados, informes y peritajes), extrae los datos de identificación (ROL/RIT, tribunal, carátula, partes, fechas, montos) y deja una **primera versión que se revisa y se corrige**, más un **informe en Word**. Todo corre **local**.

> ⚖️ **La herramienta asiste, no reemplaza la revisión del abogado.** Revise siempre el borrador y el informe antes de usarlos.

## Qué hace
- Lee **fotos (JPG/PNG) y PDF** de una carpeta.
- **Clasifica** cada documento en una categoría judicial (escritos, resoluciones, notificaciones, contratos, comprobantes, poderes, informes, otros).
- **Extrae** ROL/RIT, tribunal, carátula, partes, fechas, folios, notaría, abogados y montos.
- Genera:
  - **`Revision.html`** — borrador editable para revisar y corregir.
  - **`Informe.docx`** — informe en Word con portada, resumen por categoría, índice y fichas por documento.
  - (opcional) **PDFs ordenados por categoría**, índice y comprimidos para el Poder Judicial.

## La forma más simple: usar la aplicación

1. Descarga el paquete de la última versión publicada:
   - **Windows:** [LectorDeDocumentos-windows.zip](https://github.com/iustamedica-png/lectura-documentos/releases/latest/download/LectorDeDocumentos-windows.zip)
   - **Linux:** [LectorDeDocumentos-linux.zip](https://github.com/iustamedica-png/lectura-documentos/releases/latest/download/LectorDeDocumentos-linux.zip)
2. Descomprime el ZIP en una carpeta (por ejemplo, el Escritorio).
3. Doble clic en **`Lector de documentos`** (o `Lector de documentos.exe`).
4. Elige la carpeta del expediente, marca el tipo de documentos y presiona **Procesar documentos**.
5. Al terminar, abre **`Resultados/Revision.html`** para revisar y corregir los datos.

No hace falta instalar Python, usar la terminal ni saber navegar GitHub.
La primera vez puede tardar unos segundos en abrir; después funciona sin conexión.
El paquete pesa alrededor de 200 MB (incluye el motor de OCR y sus modelos).

> Si el enlace aún no tiene archivos (versión recién publicada), usa la instalación desde el código que aparece más abajo.

> **Aviso de Windows:** el programa no está firmado digitalmente. Si aparece
> "Windows protegió tu PC", haz clic en **Más información → Ejecutar de todas
> formas**. Es normal en programas sin firma comercial. Algunos antivirus
> pueden marcarlo como sospechoso (falso positivo de los empaquetados).

## Instalación desde el código (opcional, para informática)

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
| `Resultados/Documentos/` | PDFs **ordenados por categoría** e índices (si usas comprimir/ordenar). |
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

## Modo salud (opcional)

El repositorio trabaja por defecto en modo **judicial (legal)**. Si tu trabajo es de salud (bonos, fichas, recetas, boletas), usa el acceso **`Procesar salud`** o agrega `--perfil salud`.

Para dejarlo fijo en una carpeta, crea un archivo **`perfil.txt`** con el texto `salud`. Si la carpeta contiene un `caso.json`, la herramienta también asume el modo salud.

## Advertencias de calidad y tamaño
- **Orientación:** documentos derechos y en la **misma orientación** (mejor lectura).
- **Escrito a mano:** baja precisión; debe **revisarse especialmente**.
- **Peso (Poder Judicial):** límite **10 MB por archivo / 30 MB total**; la herramienta avisa y hay una opción que comprime los PDF.

## Privacidad
- **Todo el procesamiento es local**; no se envía nada a internet.
- El repositorio contiene **solo el programa**: los expedientes (nombres, RUT, datos del caso) **nunca** se suben. Detalles en [DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md).

## Créditos y licencia

Desarrollado en colaboración con **DeepSeek** (asistencia de IA en diseño, implementación y pruebas). La validación de los documentos y el criterio jurídico son del equipo legal.

### Licencia

**PolyForm Internal Use License 1.0.0** — texto completo en [LICENSE](LICENSE).

En simple:

- ✅ **Puedes usar la herramienta gratis dentro de tu estudio u oficina**, incluso para atender tus casos.
- ✅ **Puedes modificarla** para uso interno.
- ❌ **No puedes distribuirla, revenderla ni integrarla en un producto o servicio que ofrezcas a terceros.**

Para distribuir el software o acordar otro tipo de licencia, contacta al autor del proyecto.

> Esta es una licencia *source-available* (código disponible), no una licencia de código abierto aprobada por OSI.

## Contacto

- **Dudas, errores o mejoras:** abre un *issue* en el repositorio.
- **Licencias comerciales, distribución o adaptaciones:** abre un *issue* con el
  título “Licencia comercial” o escribe a: _(completar correo de contacto)_.

---

## Para desarrolladores
Documentación técnica (motor, perfil salud, comandos, pruebas): **[DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md)**. Perfil judicial: **[PERFIL-LEGAL.md](PERFIL-LEGAL.md)**.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m documental.cli --help
```

Comandos: `expediente`, `clasificar`, `preparar`, `procesar`, `revisor`, `informe`, `ordenar`, `compilar`.
Requiere Python 3.10+.

Perfil por defecto: **legal**. Para salud: `--perfil salud`, `DOCUMENTAL_PERFIL=salud` o `perfil.txt`.

```bash
# Inventario rápido de una carpeta judicial, sin OCR
PYTHONPATH=src .venv/bin/python -m documental.cli clasificar "expediente/" --csv inventario.csv

# Proceso completo del expediente judicial
PYTHONPATH=src .venv/bin/python -m documental.cli expediente --ordenar

# Modo salud (opcional)
PYTHONPATH=src .venv/bin/python -m documental.cli expediente --perfil salud --ordenar
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
https://github.com/iustamedica-png/lectura-documentos/releases/latest/download/LectorDeDocumentos-windows.zip
```
