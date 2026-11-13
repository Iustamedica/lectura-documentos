# Historial de cambios

Todas las versiones relevantes del proyecto. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.7.1] — 2026-11

### Corregido
- **La doctrina ya no se parte en varios documentos**: un PDF de doctrina se
  conserva como un solo ítem con todas sus páginas (`Document.paginas`), de modo
  que 5 textos completos producen 5 fichas y no decenas.
- La doctrina se detecta **antes del OCR** leyendo la capa de texto; los libros
  escaneados en carpetas `Doctrina`/`Biblioteca`/`Tesis`/`Articulos` se
  individualizan sin OCR-ear cientos de páginas.
- `--sin-dividir` fuerza “un PDF = un documento” en `expediente` y `procesar`.
- El refinador judicial ya no inventa ROL/tribunal en doctrina (falso
  “tribunal de tesis”).
- Una lista vacía de campos críticos ya no marca el documento como “faltante”:
  la doctrina queda con confianza alta.
- El índice muestra el rango completo de páginas (`pp. 1-324`) y el año.

## [0.7.0] — 2026-11

### Agregado
- **Modo biblioteca** (`documental biblioteca`): un PDF = un ítem; extrae título,
  autores, año, tipo, fuente, DOI, ISBN, idioma y páginas, y genera catálogo
  CSV/JSON con confianza por campo.
- **`documental ordenar-paginas`**: detecta el número impreso (arábigo o romano),
  valida la secuencia y escribe un PDF nuevo en orden; si es ambiguo, entrega el
  mapa de páginas sin tocar el original.
- `--reordenar`, `--salida` y `--renombrar` en el modo biblioteca.

### Limitaciones
- Los PDF sin capa de texto se marcan para OCR y no reciben ficha inventada.
- La taxonomía de materias (civil, penal, familia…) queda para una versión
  posterior.

## [0.6.0] — 2026-11

### Agregado
- **Naturaleza de la fuente**: cada documento se clasifica como `expediente`,
  `jurisprudencia`, `resolucion` (acto administrativo), `doctrina` o `documento`.
- Clasificador con negativos y marcadores editoriales (ISSN, DOI, ISBN, tesis,
  primera edición) para no confundir doctrina con jurisprudencia citada.
- Árbol de salida por fuente: `01-expedientes/`, `02-jurisprudencia/`,
  `03-resoluciones-administrativas/`, `04-doctrina/`, `05-documentos/`.
- Tipos nuevos: Libro, Capítulo, Artículo de revista, Tesis, Publicación,
  Sentencia CS/CA/TC, Resolución administrativa, Dictamen, Sanción y Sumario.
- Columna **Fuente** en el índice CSV/Word y chip `Fuente: …` en el revisor.
- Resumen “Por fuente” en el informe y campos críticos propios (doctrina no exige
  ROL; jurisprudencia exige tribunal y fecha).

### Cambiado
- Las carpetas de salida ahora tienen dos niveles cuando corresponde
  (`01-expedientes/01-escritos`, `05-documentos/02-comprobantes`).

## [0.5.1] — 2026-11

### Agregado
- Licencia **PolyForm Internal Use 1.0.0** (`LICENSE`), con resumen en el README,
  aviso en la app y copia dentro del paquete descargable.
- Contacto para licencias comerciales.

### Corregido
- `AUTHORS.md` ya no sugiere MIT.
- Se aclara que los modelos de OCR vienen incluidos (no se descargan).

## [0.5.0] — 2026-11

### Agregado
- **Mini app de escritorio** (Tkinter): elegir carpeta, modo judicial/salud,
  procesar, ver progreso y abrir resultados.
- Empaquetado con **PyInstaller** para Windows y Linux.
- Workflow de GitHub Actions que genera los ZIP y los adjunta a la Release.
- Lanzadores `Lector de documentos` y `Procesar salud`.

## [0.4.0] — 2026-11

### Cambiado
- El perfil **legal pasa a ser el predeterminado** en la CLI pública.
- El modo **salud** queda opcional: `--perfil salud`, `DOCUMENTAL_PERFIL=salud`,
  `perfil.txt` o `caso.json` en la carpeta.
- README reescrito para el público judicial.

## [0.3.0] — 2026-11

### Agregado
- Documentos **penales**: querella, denuncia, formalización, acusación,
  sobreseimiento, sentencia condenatoria/absolutoria y medidas cautelares.
- Documentos de **familia**: divorcio, alimentos, cuidado personal, relación
  directa y regular, medida de protección (VIF).
- **Campos críticos por tipo** documental (el semáforo ya no exige ROL a un
  contrato).

## [0.2.0] — 2026-11

### Agregado
- Arquitectura de **perfiles**: motor común + perfil `salud` (histórico) y
  perfil `legal`.
- Perfil legal: 8 categorías, ~40 tipos canónicos, extracción de ROL, tribunal,
  carátula, partes, fojas, notaría y montos.
- Índice con columnas judiciales, informe con resumen por categoría y revisor
  con los campos del perfil.

## [0.1.x] — 2026

- OCR local con RapidOCR + PyMuPDF.
- Clasificación y extracción de bonos, boletas, fichas, recetas y certificados.
- Comando `expediente` (revisor HTML + informe Word).
- Recursividad de carpetas y tope de píxeles al renderizar.
- Comando `clasificar` sin OCR para inventarios rápidos.
- Fusión de bloques por hoja y uso de la capa de texto en PDF digitales.
- Corrección de división por cero en páginas en blanco.
