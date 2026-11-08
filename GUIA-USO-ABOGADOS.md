# Guía rápida para abogados — Lector de documentos

Herramienta que **lee fotos y PDF** de un expediente, extrae los datos (sin subir
nada a Internet) y deja una **primera versión editable** y un **informe en Word**.

## Instalación (una sola vez)

La hace **una vez** alguien con conocimientos básicos o informática:

- **Windows:** doble clic en `instalar.bat`.
- **Linux / Mac:** doble clic en `instalar.sh` (o `bash instalar.sh`).

La **primera vez que procese** descargará los modelos de OCR (necesita internet
esa única vez). Después puede usarse sin conexión.

## Uso diario (muy simple)

1. Abra la carpeta **`Expediente`** (si no existe, se crea al primer uso).
2. Copie **todas sus fotos (JPG/PNG) y PDF** dentro de
   **`Expediente → 1. Documentos a procesar`**.
   - Pueden ser muchos archivos.
   - Ideal: **escaneos derechos y legibles** (si están torcidos o borrosos, el
     resultado será peor).
3. **Doble clic** en:
   - Windows: `Procesar documentos.bat`
   - Linux/Mac: `Procesar documentos.sh`
4. Espere. Cuando diga **“LISTO”**, se abre solo:
   - **`Expediente → Resultados → Revision.html`** → ábralo en el navegador
     para **revisar y corregir** lo que el OCR haya leído mal.
   - **`Expediente → Resultados → Informe.docx`** → el informe en Word.

## Qué hay en `Resultados`

| Archivo | Qué es |
|---|---|
| `Revision.html` | Revisor para corregir los datos detectados (abrir en el navegador). |
| `Informe.docx` | El informe Word con los documentos y sus datos. |
| `expediente.json` | Datos crudos (por si hace falta soporte técnico). |
| `render/` | Recortes de imagen que usa el revisor. |
| `Registro.txt` | Resumen del proceso, por si algo falla. |

## Consejos

- **Siempre revise** el revisor y el informe: la herramienta es un asistente, la
  responsabilidad final es del abogado.
- Si un documento no se detectó bien (fechas, RUT, montos), corrija en el revisor.
- Los datos son **sensibles** (salud): mantenga la carpeta `Expediente` en un
  equipo seguro y **no** la suba a servicios en la nube.

## ¿Algo no funciona?

Revise **`Resultados → Registro.txt`**. Si el mensaje es sobre el entorno
(`.venv`), pida que se ejecute de nuevo la instalación (paso de arriba).

## Advertencias importantes

- **Orientación:** los documentos deben estar **todos derechos y en la misma orientación**.
  Si vienen torcidos o en distinta orientación, la lectura empeora.
- **Escrito a mano:** el texto **manuscrito** tiene **baja precisión**. **Revise con especial
  cuidado** esos documentos en `Revision.html` antes de confiar en el informe.
- **Peso para el Poder Judicial:** el portal limita a **10 MB por archivo** y **30 MB en total**.
  La herramienta **avisa** si un PDF supera el límite. Si necesita reducirlo, use el launcher
  **“Procesar y comprimir (Poder Judicial)”**, que genera los PDF con menos peso (algo de
  pérdida de nitidez, pero legibles).

Siempre revise el revisor y el informe: la herramienta es un asistente, **no** reemplaza su criterio.

