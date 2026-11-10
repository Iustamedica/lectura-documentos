# Privacidad y tratamiento de datos

## Resumen

- **Todo se procesa en tu computador.** La aplicación no envía documentos,
  imágenes ni datos a internet.
- **No hay cuentas, telemetría ni analítica.** No se registra quién la usa ni qué
  procesa.
- **Los resultados quedan en tu disco**, en la carpeta `Resultados` del expediente.

## Qué datos procesa

- Las **fotos y PDF** que copias a la carpeta del expediente.
- Los datos que el OCR extrae de ellos: nombres, RUT, ROL, tribunal, fechas,
  montos y demás campos del expediente.
- El **revisor HTML** guarda tus correcciones en el almacenamiento local del
  navegador (`localStorage`) para no perderlas si cierras la pestaña. Son datos
  locales del navegador; puedes borrarlos limpiando los datos del sitio.

## Qué NO hace

- No sube archivos a la nube.
- No descarga modelos ni actualizaciones en tiempo de ejecución.
- No envía estadísticas de uso.
- No comparte datos con terceros.

## Tu responsabilidad

La herramienta es un procesador local: **tú decides dónde están los archivos y
quién tiene acceso al equipo**. Al tratar datos de clientes, aplican las normas
de protección de datos personales (en Chile, la Ley 19.628 y la Ley 21.719) y el
secreto profesional.

Recomendaciones:

- Mantén la carpeta del expediente en un equipo con clave y, si es posible,
  disco cifrado.
- No copies la carpeta `Resultados` a servicios en la nube sin las medidas de
  seguridad de tu estudio.
- Borra los resultados cuando termine el caso, si tu política interna lo exige.
- No adjuntes documentos reales en un *issue* de GitHub. Para reportar un error,
  describe el problema y adjunta solo el mensaje de `Registro.txt` sin datos.

## Alcance

Esta política cubre la aplicación de escritorio y su código. No cubre los
servicios de terceros que tú decidas usar (correo, nube, mensajería) para mover
los archivos.

## Contacto

Dudas de privacidad: abre un *issue* en el repositorio sin incluir datos
personales.
