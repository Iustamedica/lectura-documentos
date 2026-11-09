# Lector de documentos para expedientes (OCR local)

**Convierte fotos y PDF de un expediente en un borrador editable y un informe Word, en tu propio computador y sin subir nada a internet.**

Pensada para abogados: toma los documentos escaneados (bonos, boletas, recetas, fichas, certificados, escritos, etc.), extrae los datos de identificación (nombre, RUT, fechas, emisor, montos) y deja una **primera versión que se revisa y se corrige** y un **informe en Word**. Todo corre **local**.

> ⚖️ **La herramienta asiste, no reemplaza la revisión del abogado.** Revise siempre el borrador y el informe antes de usarlos.

## Dos modos de trabajo

| Modo | Para qué | Cómo se usa |
|---|---|---|
| **Salud** (por defecto) | Bonos, fichas, recetas, boletas y certificados de un expediente de salud. | Los accesos directos (`Procesar documentos`). |
| **Legal** | Escritos, resoluciones, notificaciones, contratos y prueba de un expediente judicial. | `documental expediente --perfil legal` |

El modo salud sigue funcionando **igual y local**: si no se indica perfil, la
herramienta usa salud. El catálogo y los campos del modo legal están en
**[PERFIL-LEGAL.md](PERFIL-LEGAL.md)**.

## Qué hace
- Lee **fotos (JPG/PNG) y PDF** de una carpeta.
- **Clasifica y extrae** los datos de cada documento (sin OCR cuando el PDF ya trae texto, por velocidad).
- Genera:
  - **`Revision.html`** — borrador editable para revisar y corregir.
  - **`Informe.docx`** — informe en Word.
  - (opcional) **PDFs ordenados por categoría** y comprimidos para el Poder Judicial.

## Qué necesitas
- Un computador con **Windows**, **macOS** o **Linux**.
- Documentos en **buena calidad**: derechos, legibles y **en la misma orientación**.
- La **primera vez**, internet para instalar (después funciona **sin conexión**).

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

📘 Guía detallada paso a paso: **[GUIA-USO-ABOGADOS.md](GUIA-USO-ABOGADOS.md)**.

## Qué genera
| Archivo | Para qué |
|---|---|
| `Resultados/Revision.html` | Abrir en el navegador para **revisar y corregir** los datos. |
| `Resultados/Informe.docx` | El **informe Word**. |
| `Resultados/Documentos/` | PDFs **ordenados por categoría** (si usas comprimir/ordenar). |
| `Resultados/Registro.txt` | Resumen del proceso (útil si algo falla). |

## Advertencias de calidad y tamaño
- **Orientación:** documentos derechos y en la **misma orientación** (mejor lectura).
- **Escrito a mano:** baja precisión; debe **revisarse especialmente**.
- **Peso (Poder Judicial):** límite **10 MB por archivo / 30 MB total**; la herramienta avisa y hay una opción que comprime los PDF.

## Privacidad
- **Todo el procesamiento es local**; no se envía nada a internet.
- El repositorio contiene **solo el programa**: los expedientes (datos de salud, nombres, RUT) **nunca** se suben. Detalles en [DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md).

## Créditos y licencia
Desarrollado en colaboración con **DeepSeek** (asistencia de IA en diseño, implementación y pruebas). La validación de los documentos y el criterio jurídico son del equipo legal.

> Licencia: ver `LICENSE` (a definir por el autor del proyecto).

---

## Para desarrolladores
Documentación técnica completa (comandos, arquitectura, extractores, pruebas, privacidad): **[DOCUMENTACION-TECNICA.md](DOCUMENTACION-TECNICA.md)**.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python -m documental.cli --help
```

Comandos: `expediente`, `clasificar`, `preparar`, `procesar`, `revisor`, `informe`, `ordenar`, `compilar`.
Requiere Python 3.10+.

Perfiles: `--perfil salud` (por defecto) o `--perfil legal`.

```bash
# Inventario rápido de una carpeta judicial, sin OCR
PYTHONPATH=src .venv/bin/python -m documental.cli clasificar "expediente/" --perfil legal --csv inventario.csv

# Proceso completo del expediente legal
PYTHONPATH=src .venv/bin/python -m documental.cli expediente --perfil legal --ordenar
```
