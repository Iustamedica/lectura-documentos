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

## Inicio rápido (2 pasos)

**1) Instalar (una sola vez)**
- **Windows:** doble clic en `instalar.bat`.
- **Linux/Mac:** doble clic en `instalar.sh` (o `bash instalar.sh`).

**2) Usar**
1. Abre la carpeta **`Expediente`** (se crea sola).
2. Copia tus **fotos y PDF** en **`Expediente/1. Documentos a procesar`**.
3. Doble clic en:
   - **`Procesar documentos`** — genera el borrador y el Word.
   - **`Procesar y comprimir (Poder Judicial)`** — igual, y comprime los PDF a los límites de carga.
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

> Licencia: ver `LICENSE` (a definir por el autor del proyecto).

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
