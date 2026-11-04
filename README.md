# Extractor documental (OCR local) para expedientes de salud

Herramienta local que lee PDF escaneados (boletas, bonos FONASA, recetas,
tickets de farmacia, pagares) **sin subir nada a internet**, extrae los datos de
identificacion y montos, y genera un **informe Word** para el abogado.

Todo el procesamiento ocurre en el equipo: se usa [RapidOCR](https://github.com/RapidAI/RapidOCR)
(ONNX Runtime) en lugar de Tesseract, porque Tesseract no estaba disponible en
este entorno y RapidOCR rinde mejor con escaneos de baja resolucion en espanol.

> ## AVISO DE PRIVACIDAD (leer antes de subir datos)
>
> Este repositorio contiene **solo codigo**. Los datos de pacientes (nombres,
> RUT, direcciones, diagnosticos, montos) son **datos sensibles de salud** y no
> deben versionarse. Antes de hacer `git add`, verifique:
>
> - `caso.json` esta en `.gitignore`. Use `caso.ejemplo.json` como plantilla.
> - Los escaneos (`escaneos*/`, `*.pdf`) estan en `.gitignore`.
> - `salidas/` esta en `.gitignore` (contiene texto OCR e informes con datos).
> - Los ejemplos del codigo y de los tests son **ficticios**
>   (`GLORIA ESTER SOTO PEREZ`, `12.345.678-5`). No los reemplace por datos
>   reales al adaptar la herramienta.
>
> Si ya subio datos por error: **no basta con borrar el commit**. El historial de
> Git conserva los blobs y GitHub los mantiene accesibles por URL y en forks.
> Hay que reescribir el historial (`git filter-repo`) o eliminar el repositorio,
> y ademas notificar a GitHub. Para un repositorio privado compartido con un
> colega, conviene ademas activar 2FA y dar acceso minimo.

---

## 1. Instalacion (entorno aislado, sin tocar el sistema)

```bash
cd "herramientas/documental"

python3 -m venv .venv                     # entorno virtual propio
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

Verificar:

```bash
.venv/bin/python -m pytest -q             # pruebas unitarias
```

> **Por que un venv**: evita conflictos con el Python del sistema operativo y
> permite borrar todo el entorno con `rm -rf .venv` sin dejar residuos.

### Uso sin instalacion (desarrollo)

```bash
PYTHONPATH=src .venv/bin/python -m documental.cli --help
```

### Atajos (scripts incluidos)

```bash
# 1) crear la configuracion del caso a partir de la plantilla
cp caso.ejemplo.json caso.json      # luego editar con los datos reales

# 2) procesar
./ejecutar.sh              # OCR + extraccion + revisor (usa ../../escaneos-csm)
./ejecutar.sh /ruta/a/otra/carpeta

# si los documentos son fotos de celular, primero:
.venv/bin/python -m documental.cli preparar /ruta/fotos --destino salidas/pdf

# tras corregir y exportar expediente_corregido.json en salidas/
./informe.sh               # genera salidas/informe.docx
.venv/bin/python -m documental.cli compilar salidas/expediente_corregido.json \
    --origen salidas/pdf   # genera salidas/documentos.pdf + individualizacion
```

`caso.json` (datos del caso) esta en `.gitignore`: **nunca** se versiona. El
repositorio solo incluye `caso.ejemplo.json` con datos ficticios.


---

## 2. Flujo de trabajo

```
Fotos (JPG/PNG)                      PDF escaneados
     |                                     |
     v                                     |
[0] preparar -> PDF sin perder resolucion  |
     |                                     |
     +------------------+------------------+
                        v
[1] procesar  ->  OCR + clasificacion + extraccion  ->  salidas/expediente.json
                                                    ->  salidas/render/*.png (recortes)
     |
     v
[2] revisor.html  ->  revision humana en el navegador  ->  expediente_corregido.json
     |
     v
[3] informe   ->  salidas/informe.docx          (analisis por titular)
[4] compilar  ->  salidas/documentos.pdf        (un solo PDF para el tribunal)
              ->  salidas/individualizacion.docx/.csv  (tabla del escrito)
```

### Paso 0: convertir fotos a PDF (solo si los documentos son fotos)

```bash
.venv/bin/python -m documental.cli preparar ../../escaneos-postqx \
    --destino salidas/pdf --unir-por-tiempo 35
```

Convierte cada foto en una hoja de PDF **sin reducir su resolucion**: el tamano
de pagina se calcula desde los pixeles a 300 dpi, de modo que al volver a
renderizar se recuperan los mismos pixeles (una foto de 2779 x 3549 px da una
pagina de 667 x 852 pt).

`--unir-por-tiempo SEGUNDOS` propone agrupar en un mismo PDF las fotos tomadas
con menos de N segundos de diferencia, porque suelen ser las hojas del mismo
documento. Es **una propuesta**, no una certeza: queda registrada en
`salidas/mapa_fotos.csv` para revisarla. Con `0` (por defecto) no agrupa nada.

Para revisar el plan sin escribir archivos: agregue `--dry-run`.

### Paso 1: procesar la carpeta de escaneos

```bash
.venv/bin/python -m documental.cli procesar ../../escaneos-csm \
    --json salidas/expediente.json \
    --render salidas/render \
    --html salidas/revision.html \
    --titulares caso.json
```

Tarda unos 10 segundos por pagina (CPU, sin GPU). Se puede lanzar en segundo
plano:

```bash
nohup .venv/bin/python -m documental.cli procesar ../../escaneos-csm \
    --json salidas/expediente.json --render salidas/render \
    --titulares caso.json > /tmp/proceso.log 2>&1 &
```

### Paso 2: revisar y corregir en el navegador

Abrir `salidas/revision.html` con doble clic (funciona sin internet). Se ve cada
documento con su recorte, sus campos y una marca de confianza:

- **Verificado**: lectura segura (por ejemplo RUT con digito verificador correcto).
- **Probable**: patron reconocido con ruido de OCR.
- **Verificar**: requiere contraste con el papel.
- **Faltante**: no se pudo obtener.

Al corregir un valor, el campo se marca como `edited` y sube a "Verificado".
El boton **Exportar JSON corregido** descarga `expediente_corregido.json`
(guardar dentro de `salidas/`). Los cambios tambien quedan en el
`localStorage` del navegador por si se cierra la pestana.

### Paso 3: generar el informe Word

```bash
.venv/bin/python -m documental.cli informe salidas/expediente_corregido.json \
    --docx salidas/informe.docx --render salidas/render
```

El `.docx` se abre en Word, LibreOffice u Obsidian.

### Paso 4: compilar el PDF del tribunal y la tabla de individualizacion

```bash
.venv/bin/python -m documental.cli compilar salidas/expediente_corregido.json \
    --origen salidas/pdf \
    --pdf salidas/documentos.pdf \
    --csv salidas/individualizacion.csv \
    --docx salidas/individualizacion.docx
```

Genera tres cosas:

1. **`documentos.pdf`**: un solo PDF con todos los documentos, en orden
   cronologico. En la primera hoja de cada uno estampa el bloque de
   identificacion que usa el escrito:

   ```
   DOCUMENTO N 3
   NOMBRE: GLORIA ESTER SOTO PEREZ
   RUT: 12.345.678-5
   TIPO: Bono de atencion FONASA      FECHA: 12-03-2026
   EMISOR: HOSPITAL DE EJEMPLO        FOLIO: 1234
   ```

   El encabezado **amplia la hoja hacia arriba**, no se escribe encima: el
   documento original nunca queda tapado ni se pierde margen. Cada documento
   queda ademas como marcador del PDF, para saltar entre ellos en el visor.

2. **`individualizacion.docx` / `.csv`**: la tabla del escrito (N, tipo, fecha,
   emisor, titular, RUT, folio, monto, archivo y pagina de origen).

3. **Los documentos sin fecha legible quedan al final**, no intercalados.

Con `--sin-estampar` compila sin encabezado. Con `--dry-run` no escribe el PDF,
pero si la tabla, para revisar el resultado antes de generarlo.

`--origen` se puede repetir tantas veces como carpetas haya (por ejemplo
`--origen salidas/pdf --origen ../../escaneos-csm`).

**La numeracion `DOC-NN` es una propuesta.** Se calcula agrupando las hojas
consecutivas del mismo archivo que comparten familia, folio y titular. Si un
documento quedo mal unido o separado, corrija la fecha o el folio en el revisor
y vuelva a compilar.

### Regenerar sin repetir el OCR

Si cambia la logica de agrupacion de titulares (o `caso.json`) y no quiere
esperar los ~10 minutos del OCR, use `regenerar.py` sobre el expediente ya
calculado. Reagrupa los titulares con la logica vigente y reescribe el JSON, el
revisor y el Word:

```bash
.venv/bin/python regenerar.py salidas/expediente.json --titulares caso.json \
    --html salidas/revision.html --docx salidas/informe.docx --render salidas/render
```

Tenga en cuenta que este atajo **no** vuelve a extraer campos de los documentos:
solo reagrupa. Si el cambio esta en un extractor (por ejemplo, como se elige el
RUT del paciente), hay que volver a correr `./ejecutar.sh`.

---

## 3. Que contiene el informe

1. **Portada** con carpeta de origen, cantidad de documentos, titulares y aviso
   metodologico (los datos provienen de OCR).
2. **Resumen por titular**: documentos y monto total por persona. Si un titular
   no tiene RUT verificado aparece **POR CONFIRMAR** en rojo.
3. **Indice de documentos**: tabla consolidada (tipo, titular, RUT, fecha,
   emisor, total, estado).
4. **Fichas por documento**: todos los campos con su nivel de confianza, el
   detalle de prestaciones/productos y el recorte de la imagen original.
5. **Anexo de verificacion**: lista de todos los datos marcados "Verificar" o
   "Faltante" para contrastar con el papel, mas las advertencias del proceso.

---

## 4. Multiples titulares en un mismo expediente

Un expediente puede tener documentos de varias personas (por ejemplo la madre y
el hijo). Los documentos se agrupan **por RUT**, y el parentesco se declara en
`caso.json`:

```json
{
  "titulares": [
    {"rut": "12.345.678-5", "nombre": "GLORIA ESTER SOTO PEREZ",
     "relacion": "titular principal", "alias": ["GLORIA ESTER SOTO"]},
    {"rut": "", "nombre": "LUIS ANDRES SOTO PEREZ",
     "relacion": "hijo de la titular principal",
     "notas": "RUT pendiente de confirmar"}
  ]
}
```

La agrupacion se hace en **dos fases**, para que el resultado no dependa del
orden en que aparecen los archivos:

1. Se agrupan los documentos que traen RUT valido (el RUT manda).
2. Los documentos sin RUT se cotejan por nombre contra los grupos ya formados y
   se suman al que corresponda. Si no calzan con ninguno, forman su propio grupo.

Esto evita el error clasico de un expediente real: FONASA imprime
`APELLIDOS NOMBRES` ("SOTO PEREZ GLORIA ESTER") y la boleta al reves
("GLORIA ESTER SOTO PEREZ"). Si el documento con nombre y sin RUT llegara
antes, una agrupacion en una sola pasada crearia dos titulares para la misma
persona.

Reglas:

- Nunca se inventa un RUT: si no aparece en el documento, queda vacio y el
  informe lo muestra como "POR CONFIRMAR".
- El cotejo por nombre tolera palabras faltantes y palabras truncadas por el
  OCR ("GLORIA ESTER SOT" se reconoce como "GLORIA ESTER SOTO PEREZ"), pero
  exige al menos dos palabras de 3+ letras para no unir personas distintas.
- El `alias` ayuda a reconocer el nombre cuando el OCR lo corta.
- Cuando `caso.json` declara nombre y parentesco, esos son los que se informan;
  el OCR solo los completa si faltan.
- El RUT de un medico **nunca** crea un titular. En las recetas oftalmologicas
  el RUT del profesional aparece suelto ("Rp. RUT: 11.111.111-1") y antes se
  convertia en un titular de nombre vacio; hoy se descarta como RUT del titular
  y se guarda como RUT del profesional.
- Los montos se suman por titular; los documentos sin titular identificado no se
  asignan a nadie y se listan en el anexo.

---

## 5. Familias de documentos soportadas

| Familia | Extractor | Datos que extrae |
|---|---|---|
| Bono FONASA / Programa de salud | `extractors/fonasa.py` | folio, RUT y nombre del beneficiario, edad, prevision, fecha, hora, bruto, bonificacion, copago, total |
| Boleta electronica SII | `extractors/sii.py` | emisor y RUT, giro, folio, titular y RUT, fecha, neto, IVA, total, items |
| Ticket de farmacia | `extractors/otros.py` | cadena, folio, fecha, RUT del cliente, total |
| Receta optica | `extractors/otros.py` | paciente, fecha, profesional, medidas (ESF/CIL/EJE/DP) |
| Receta medica manuscrita | `extractors/otros.py` | RUT del medico, especialidad; paciente inferido y marcado "Verificar" |
| Documento clinico | `extractors/otros.py` | paciente, fecha, diagnostico |
| Pagare | `extractors/otros.py` | folio, emisor, RUT, capital adeudado |
| Comprobante de tarjeta (Transbank/KLAP) | `pipeline.py` | se adjunta al documento anterior como medio de pago |

Si la familia no se reconoce, se aplica un extractor generico que busca RUT de
persona, fecha y montos por proximidad, y el documento queda marcado para
revision.

---

## 6. Decisiones de diseno relevantes

- **RUT de persona vs. empresa**: en Chile los RUT de personas naturales son
  menores a 30 millones; los de clinicas, opticas y fundaciones superan los 65
  millones. Esto evita asignar el RUT del prestador al paciente (problema real
  detectado en estos escaneos: las recetas del Dr. Fuentes traen impreso su
  propio RUT).
- **Digito verificador**: se valida con modulo 11 antes de aceptar un RUT, lo
  que descarta casi todos los falsos positivos del OCR.
- **Fechas con ruido**: el OCR convierte digitos en letras (`4-0I-20026` ->
  `04-01-2026`); solo se aplican las correcciones que producen una fecha valida.
- **Nunca perder un documento**: si un extractor falla, el error se registra en
  el propio documento y el lote continua.
- **Trazabilidad**: cada campo guarda el fragmento de OCR del que se obtuvo
  (`raw`), su nivel de confianza y una nota cuando hay inconsistencia.
- **OCR una sola vez**: el OCR es la etapa lenta (~10 s por pagina en CPU). Las
  recetas manuscritas necesitan conocer los nombres del expediente para
  reconstruir el paciente, por lo que esas paginas se reprocesan reutilizando el
  OCR ya calculado, sin volver a leer el PDF. En este expediente (20 PDF, 30
  paginas) el proceso completo tarda ~8-10 minutos.

---

## 7. Limitaciones conocidas

- Los escaneos aportados tienen ~1024 px de alto; la letra pequena (tickets de
  farmacia, textos legales de pagares) se lee mal. **Escaneos nuevos a 300 dpi
  mejoran notablemente el resultado**; `--dpi` permite ajustar el render.
- Los documentos manuscritos dependen de un OCR pensado para texto impreso.
- Los estados de cuenta financieros (banco, caja de compensacion) no tienen
  extractor propio: se procesan con el generico y se marcan para revision.
- No se calculan intereses, reajustes ni prescripciones; el informe solo
  transcribe y consolida lo que dicen los documentos.

Limitaciones especificas de la agrupacion de titulares:

- **Nombres manuscritos destruidos por el OCR.** El paciente se infiere de otros
  documentos del expediente, pero queda con confianza *baja* y una nota que pide
  confirmar contra el original. Si en ningun documento aparece una palabra util
  del nombre, el documento no se asigna a nadie (se lista en el anexo), en vez de
  adivinar.
- **Documentos que no nombran al paciente ni traen su RUT.** Quedan sin titular
  y no se reparten por proximidad de fechas: para un informe que se presenta en
  tribunales preferimos dejarlos en el anexo antes que atribuirlos por
  suposicion.
- **Nombres parecidos dentro del mismo grupo familiar** (por ejemplo padre e
  hijo homonimos). El cotejo exige dos palabras coincidentes, por lo que un
  nombre muy truncado podria no reconocerse; aparece entonces como titular
  aparte y el revisor HTML lo deja corregir a mano.
- **Un nombre muy mal leido no se fuerza.** Si el OCR devuelve un texto que no
  calza con ningun titular, se emite una advertencia de titular sin emparejar en
  vez de fusionarlo en silencio.

Limitaciones de la conversion de fotos y de la individualizacion:

- **La agrupacion por tiempo encadena.** `--unir-por-tiempo` compara cada foto
  con la anterior, no con la primera del grupo. En un lote real de 85 fotos los
  intervalos dentro de un documento fueron de 6 a 34 s y los de entre documentos
  de 39 s o mas, de modo que 35 s es un corte razonable; pero una sesion en la
  que se fotografia sin pausa (13 fotos seguidas cada ~13 s) se une en un solo
  documento aunque sean varios. Revise siempre `mapa_fotos.csv`.
- **La reduccion a 2200 px no acelera de forma notoria.** Medido sobre fotos de
  2779 x 3549 px: 28,5 s frente a 31,2 s (unos 10 %), con texto extraido
  identico. RapidOCR ya normaliza el tamano internamente; `--target-height`
  sirve para acotar memoria, no para ganar tiempo.
- **La tabla de individualizacion solo puede mostrar lo que el OCR leyo.** En el
  lote de fotos de prueba, 2 de 5 documentos quedaron con nombre y fecha; el
  resto aparece con `-`. Un RUT ausente en la tabla no significa que el
  documento no lo tenga: significa que el OCR no lo reconocio. Corrijalo en el
  revisor antes de compilar.
- **La numeracion `DOC-NN` no se edita desde el revisor todavia.** Se recalcula
  al compilar a partir de la fecha corregida y del orden de los archivos. Si
  necesita un orden manual distinto, la via actual es ajustar la fecha de
  emision en el revisor.
- **Un documento puede ocupar varias paginas o compartir hoja con otro.** La
  agrupacion une hojas consecutivas del mismo archivo con igual familia, folio y
  titular; ante la duda deja documentos separados.

---

## 8. Estructura del proyecto

```
herramientas/documental/
├── caso.json                  # titulares del caso (RUT, nombre, parentesco)
├── ejecutar.sh                # OCR + extraccion + revisor HTML
├── informe.sh                 # Word desde el JSON corregido
├── regenerar.py               # rehace JSON/revisor/Word sin repetir el OCR
├── requirements.txt
├── pyproject.toml
├── src/documental/
│   ├── normalizers.py         # RUT, CLP, fechas, nombres
│   ├── ocr.py                 # RapidOCR + render de PDF + preprocesado
│   ├── ingesta.py             # fotos -> PDF sin perder resolucion
│   ├── layout.py              # lineas y bloques (varios documentos por hoja)
│   ├── classify.py            # familia documental por palabras clave
│   ├── models.py              # Field, Document, Titular, Expediente
│   ├── extractors/            # un modulo por familia documental
│   ├── titulares.py           # agrupacion por RUT y parentesco
│   ├── pipeline.py            # orquestacion de punta a punta
│   ├── individualizacion.py   # agrupar hojas, numerar DOC-NN, tabla del escrito
│   ├── compilar.py            # PDF unico con encabezado estampado y marcadores
│   ├── report_docx.py         # informe Word
│   ├── revisor.py             # revisor HTML autocontenido
│   └── cli.py                 # linea de comandos
└── tests/                     # pruebas unitarias
```

---

## 9. Privacidad

No hay llamadas a servicios externos en tiempo de ejecucion. Los modelos ONNX se
descargan **una sola vez** durante `pip install` (quedan dentro de `.venv`) y
luego el sistema funciona totalmente offline. Los datos de salud nunca salen del
equipo.


