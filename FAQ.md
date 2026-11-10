# Preguntas frecuentes (FAQ)

## Privacidad y funcionamiento

**¿Sube mis documentos a internet?**
No. Todo el procesamiento (OCR, clasificación, informe) ocurre en tu computador.
La aplicación no envía archivos ni datos a ningún servidor.

**¿Necesito internet para usarla?**
No, una vez instalada o descomprimida. Los modelos de OCR vienen incluidos en el
paquete; la primera apertura puede tardar unos segundos, pero no descarga nada.

**¿Guarda mis datos en algún lado?**
Solo en tu disco: la carpeta `Resultados` del expediente. El revisor HTML guarda
tus correcciones en el navegador (`localStorage`) para no perderlas si cierras la
pestaña; puedes borrarlas limpiando los datos del navegador.

**¿Puedo usarla en un computador compartido?**
Sí, pero recuerda que los documentos quedan en disco. Usa una carpeta segura y
borra los resultados cuando termines.

## Instalación y avisos del sistema

**Windows dice “Windows protegió tu PC”. ¿Es virus?**
No. El programa no está firmado digitalmente (la firma cuesta un certificado
anual). Haz clic en **Más información → Ejecutar de todas formas**.

**Mi antivirus lo marca como sospechoso.**
Es un falso positivo habitual de los programas empaquetados con PyInstaller.
Puedes agregar la carpeta a las exclusiones del antivirus.

**¿Funciona en Mac?**
El código es compatible, pero por ahora publicamos paquetes para **Windows** y
**Linux**. En Mac se puede instalar desde el código (ver README).

**¿Por qué el ZIP pesa ~200 MB?**
Incluye Python, el motor de OCR (ONNX Runtime) y sus modelos. No requiere
instalar nada más.

## Uso diario

**¿Qué archivos acepta?**
PDF, JPG, PNG y TIFF. Pueden estar sueltos o en subcarpetas.

**No encuentra mis documentos.**
Verifica que elegiste la carpeta correcta y que los archivos tienen esas
extensiones. La carpeta puede contener subcarpetas.

**¿Lee documentos escritos a mano?**
Muy limitadamente. El texto manuscrito tiene baja precisión: revísalo siempre en
`Revision.html`.

**¿Qué pasa si los documentos están torcidos?**
El OCR empeora. Idealmente escanéalos derechos y en la misma orientación.

**¿Cuánto demora?**
Depende de la cantidad de páginas y de si son escaneos o PDF digitales. Los PDF
con texto se procesan muy rápido; los escaneos requieren OCR y tardan más.

**¿Puedo procesar varios casos a la vez?**
Sí: usa **una carpeta por caso** y procésalos por separado. No mezcles
expedientes distintos en la misma carpeta.

**¿Dónde quedan los resultados?**
En `<tu carpeta>/Resultados/`: `Revision.html`, `Informe.docx`, `expediente.json`
y, si marcaste ordenar, la carpeta `Documentos/`.

**¿Cuál es la diferencia entre `Revision.html` e `Informe.docx`?**
`Revision.html` sirve para **corregir**; `Informe.docx` es el documento de
trabajo con la primera versión de los datos.

**¿Cómo actualizo el informe después de corregir?**
Exporta el JSON corregido desde `Revision.html` y usa **“Actualizar informe con
correcciones”** en la app. Se genera `Informe-corregido.docx`.

**El portal del Poder Judicial rechaza el archivo por tamaño.**
El límite es **10 MB por archivo / 30 MB total**. Marca la opción de comprimir al
procesar, o vuelve a procesar con `--ordenar --comprimir`.

## Licencia y soporte

**¿Puedo usarla en mi estudio?**
Sí, es gratuita para uso interno del estudio, incluido el trabajo de tus casos.

**¿Puedo venderla o entregarla a otra persona?**
No. La licencia PolyForm Internal Use prohíbe distribuir el software o
incorporarlo en un producto/servicio ofrecido a terceros. Para eso, escribe al
autor.

**¿Da garantía?**
No. Se entrega “tal cual”; la revisión y el uso profesional son responsabilidad
de quien la utiliza. Ver [AVISO-LEGAL.md](AVISO-LEGAL.md).

**¿Cómo reporto un error?**
Abre un *issue* en el repositorio con el sistema operativo, el paso que falló y
el mensaje de `Resultados/Registro.txt` (sin datos personales).
