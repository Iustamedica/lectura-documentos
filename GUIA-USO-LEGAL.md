# Guía de uso — Modo judicial (legal)

Esta guía es para abogadas y abogados que **no usan GitHub ni la terminal**.
La herramienta convierte fotos y PDF de un expediente en un borrador editable y
un informe Word, **sin subir nada a internet**.

## 1. Requisitos

- Windows 10 u 11 (o Linux/macOS).
- ~500 MB de espacio libre.
- Los documentos en **buena calidad**: derechos, legibles y en la misma orientación.

## 2. Instalar (una sola vez)

1. Descarga el ZIP de la última versión:
   - **Windows:** `LectorDeDocumentos-windows.zip`
   - **Linux:** `LectorDeDocumentos-linux.zip`
2. Descomprímelo en una carpeta (por ejemplo, el Escritorio).
3. Abre la carpeta y haz **doble clic en `Lector de documentos`**.

> Si Windows muestra “Windows protegió tu PC”, haz clic en **Más información →
> Ejecutar de todas formas**. El programa no está firmado digitalmente.

## 3. Preparar el expediente

1. Crea una carpeta para el caso (por ejemplo, `Escritorio/Expediente Pérez`).
2. Copia ahí **todas** las fotos (JPG/PNG) y PDF del expediente.
   - Pueden ser muchos archivos y estar en subcarpetas.
   - Ideal: escaneos derechos y legibles.
   - No hace falta renombrar nada.

## 4. Procesar

1. Abre **`Lector de documentos`**.
2. En **“Carpeta del expediente”**, elige la carpeta del caso.
3. En **“Tipo de documentos”**, deja **Judicial**.
4. (Opcional) Marca **“ordenar por categoría y comprimir para el Poder Judicial”**.
5. Presiona **Procesar documentos** y espera. La ventana muestra el avance.
6. Al terminar, presiona **Abrir resultados**.

## 5. Revisar y corregir

1. En la carpeta `Resultados`, abre **`Revision.html`** (doble clic).
2. Revisa cada documento. Los campos en rojo son los que hay que confirmar.
3. Corrige lo que el OCR leyó mal.
4. Usa **“Exportar JSON corregido”** al final de la página.
5. Vuelve a la app y presiona **“Actualizar informe con correcciones”**;
   elige el archivo `expediente_corregido.json` que acabas de descargar.
6. Se genera **`Informe-corregido.docx`** con tus correcciones.

## 6. Qué obtienes

| Archivo | Para qué |
|---|---|
| `Resultados/Revision.html` | Revisar y corregir los datos. |
| `Resultados/Informe.docx` | Primera versión del informe. |
| `Resultados/Informe-corregido.docx` | Informe con tus correcciones (si lo generaste). |
| `Resultados/Documentos/` | PDFs separados por categoría (si marcaste ordenar). |
| `Resultados/Documentos/indice.csv` | Índice para Excel. |
| `Resultados/Registro.txt` | Detalle técnico, útil si algo falla. |

## 7. Consejos

- **Revisa siempre** el revisor y el informe: la herramienta es un asistente, no
  reemplaza el criterio del abogado.
- Documentos **torcidos o manuscritos** producen más errores: revísalos con
  especial cuidado.
- Si un documento no aparece, revisa que el archivo esté en la carpeta y que no
  sea una imagen corrupta.
- Para el Poder Judicial, el portal limita **10 MB por archivo / 30 MB total**;
  la opción de comprimir deja los PDF dentro de esos límites.

## 8. Si algo falla

1. Abre `Resultados/Registro.txt` y lee la última línea.
2. Consulta **[FAQ.md](FAQ.md)**.
3. Si persiste, abre un *issue* en el repositorio indicando:
   - sistema operativo,
   - qué paso falló,
   - el mensaje de `Registro.txt` (sin datos personales).
