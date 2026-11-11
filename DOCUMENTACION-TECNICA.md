# Documentación técnica

Visión general del repositorio para quien mantiene o adapta la herramienta.
El detalle del motor y del modo salud está en
[DOCUMENTACION-MOTOR-Y-SALUD.md](DOCUMENTACION-MOTOR-Y-SALUD.md); el catálogo
judicial, en [PERFIL-LEGAL.md](PERFIL-LEGAL.md).

## 1. Arquitectura

El motor es común a todos los dominios; **un perfil** define qué documentos
conoce, cómo los clasifica, qué datos extrae y cómo los ordena.

```
PDF / fotos
   │
   ▼
[ ingesta ] → [ OCR / capa de texto ] → [ layout ] → [ clasificación del perfil ]
   → [ extracción del perfil ] → [ consolidación por hoja ]
   → [ refinamiento ] → [ agrupación e individualización ]
   → Revisor.html + Informe.docx + PDFs ordenados + índice
```

| Capa | Módulos | Responsabilidad |
|---|---|---|
| Motor | `ingesta.py`, `ocr.py`, `sinocr.py`, `layout.py`, `compilar.py`, `revisor.py`, `normalizers.py` | Leer, rasterizar, OCR, líneas/bloques, PDF final, revisor HTML, RUT/fechas/montos. |
| Modelo | `models.py`, `individualizacion.py`, `titulares.py` | `Field` con confianza, `Document`, `Expediente`, agrupación y numeración. |
| Perfiles | `perfiles/` | Catálogo, clasificación, **naturaleza de la fuente**, extracción, campos críticos, informe. |
| Salidas | `organizar.py`, `report_docx.py` | Carpetas por categoría, índice, Word. |
| Interfaces | `cli.py`, `gui.py` | Línea de comandos y mini app de escritorio. |

## 2. Estructura

```
src/documental/
  ocr.py, ingesta.py, layout.py, compilar.py, revisor.py, normalizers.py
  models.py, individualizacion.py, titulares.py
  organizar.py, report_docx.py
  cli.py, gui.py
  biblioteca.py       # modo doctrina: ficha, catalogo, reordenado
  ordenar_paginas.py  # detecta el numero impreso y reordena el PDF
  perfiles/
    base.py        # contrato Perfil
    registro.py    # get_perfil("salud"|"legal")
    config.py      # resolver_perfil (carpeta/JSON/entorno)
    salud.py       # adaptador al código histórico
    legal/
      catalogo.py      # categorías, tipos, campos, extracción
      clasificacion.py # familias con palabras clave y negativos
      naturaleza.py    # fuente: expediente, jurisprudencia, resolución...
      extractores.py
tests/            # 222 pruebas
empaquetar/       # PyInstaller + scripts de build
scripts/salud/    # flujo avanzado del modo salud (bash)
```

## 3. Perfiles

- `salud`: bonos, fichas, recetas, boletas, certificados (código histórico).
- `legal`: escritos, resoluciones, notificaciones, contratos, comprobantes,
  poderes, informes; civil, laboral, penal y familia.

Resolución del perfil en la CLI, en orden:

1. `--perfil legal|salud`
2. `DOCUMENTAL_PERFIL`
3. `perfil.txt` en la carpeta
4. `caso.json` en la carpeta → salud
5. perfil guardado en el `expediente.json`
6. **legal** por defecto

El perfil usado se guarda en el JSON, de modo que `informe`, `ordenar` y
`compilar` no necesitan repetir la bandera.

### 3.1 Naturaleza de la fuente

Además de la familia funcional, `naturaleza.py` clasifica la **fuente** con
puntajes y negativos: `expediente` (ROL/RIT, “en lo principal”), `jurisprudencia`
(Corte Suprema, “considerando”), `resolucion` (resolución exenta, dictamen,
sumario), `doctrina` (ISSN/DOI/ISBN, tesis, edición) y `documento` (boleta,
factura, contrato, carta).

El resultado se guarda en `Document.naturaleza` y `naturaleza_confianza`, se
expone en el revisor (`Fuente: …`), en la columna `naturaleza` del índice y
determina el primer nivel del árbol de salida:

```
01-expedientes/  02-jurisprudencia/  03-resoluciones-administrativas/
04-doctrina/     05-documentos/
```

## 4. Comandos

```bash
documental preparar   <fotos> --destino salidas/pdf
documental procesar   <carpeta> --json salidas/expediente.json
documental revisor    salidas/expediente.json --html salidas/revision.html
documental informe    salidas/expediente.json --docx salidas/informe.docx
documental compilar   <json> --origen <carpeta> --pdf salidas/documentos.pdf
documental ordenar    <json> --origen <carpeta> --destino V.1
documental clasificar <carpeta> --csv inventario.csv
documental expediente --carpeta <carpeta> --ordenar --comprimir
documental biblioteca <carpeta> --catalogo catalogo.csv [--reordenar --salida dir]
documental ordenar-paginas <pdf> -o <salida.pdf>
```

`expediente` es el flujo completo (revisor + Word). Sin `--perfil`, resuelve
según la sección anterior.

## 5. Datos y confianza

Cada dato es un `Field` con `value`, `confidence` (`alta`/`media`/`baja`/`faltante`),
`raw` (texto de origen), `note` y `edited`. Las correcciones del revisor se
exportan como JSON plano y `Document.from_dict` las recupera (incluidos los
campos del perfil).

Los campos críticos dependen del perfil y del tipo documental
(`Perfil.criticos_de`).

## 6. Pruebas

```bash
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m pytest -q
```

Cubren normalización, OCR con capa de texto, clasificación, extracción,
consolidación por hoja, individualización, perfiles, revisor, empaquetado básico
y la interfaz.

## 7. Empaquetado

```bash
bash empaquetar/empaquetar_linux.sh      # Linux
empaquetar\empaquetar_windows.bat        # Windows
```

PyInstaller genera `dist/LectorDeDocumentos/` con el intérprete, ONNX Runtime,
los modelos de RapidOCR, la plantilla del revisor y `LICENSE`.

El workflow `.github/workflows/empaquetar.yml` construye Windows y Linux al
publicar un tag `v*` y adjunta los ZIP a la Release. El enlace estable es:

```
https://github.com/<usuario>/<repo>/releases/latest/download/LectorDeDocumentos-windows.zip
```

## 8. Publicación

1. Subir cambios y crear un tag: `git tag -a vX.Y.Z -m "..." && git push origin main --tags`.
2. Verificar la pestaña **Actions** (debe generar los dos ZIP).
3. Completar la Release si hace falta.
4. Probar el ZIP en un equipo limpio (sin Python).

## 9. Modo biblioteca

- `biblioteca.py` trata cada PDF como un ítem: extrae la ficha de la portada
  (bloque de mayor tamaño), la página de copyright, los metadatos y el nombre del
  archivo, y guarda la confianza de cada campo.
- `ordenar_paginas.py` detecta el número impreso (arábigo o romano), exige que la
  secuencia sea única y continua, y escribe un PDF nuevo. Si no puede, devuelve el
  mapa `página_pdf → número_impreso` sin tocar el original.
- Los PDF sin capa de texto se marcan `requiere OCR`: no se inventan metadatos.
- La taxonomía de materias (civil, penal, familia, etc.) queda para una versión
  posterior; hoy el catálogo guarda la ficha bibliográfica y el tipo documental.

## 10. Licencia

PolyForm Internal Use 1.0.0 (ver [LICENSE](LICENSE)): uso interno gratuito, sin
distribución ni reventa. Las contribuciones se licencian igual
([CONTRIBUTING.md](CONTRIBUTING.md)).
