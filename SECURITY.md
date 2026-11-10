# Política de seguridad

## Alcance

Esta es una aplicación **local** de escritorio. No expone servicios de red ni
recibe conexiones. Los riesgos relevantes son:

- abrir documentos PDF maliciosos (los procesa PyMuPDF);
- exposición de datos del expediente en equipos compartidos;
- dependencias de terceros (PyMuPDF, RapidOCR, ONNX Runtime, Pillow, python-docx).

La aplicación **no** envía datos a internet ni recopila telemetría.

## Versiones soportadas

| Versión | Soporte |
|---|---|
| 0.5.x | Sí |
| ≤ 0.4.x | Solo actualización recomendada |

## Cómo reportar una vulnerabilidad

**No abras un issue público con datos sensibles.** Usa uno de estos canales:

1. **GitHub Security Advisory** (recomendado): pestaña *Security → Report a
   vulnerability* del repositorio.
2. Si no está disponible, abre un *issue* indicando solo “reporte de seguridad”
   y un medio de contacto; no incluyas documentos, nombres, RUT ni rutas con
   datos de clientes.

Incluye:

- versión de la app y sistema operativo;
- pasos para reproducir;
- impacto estimado.

## Compromisos

- Responder el reporte en un plazo razonable.
- Publicar la corrección en una versión nueva y acreditar el reporte si la
  persona lo autoriza.
- No compartir documentos de clientes en la investigación.

## Recomendaciones para usuarios

- Mantén el sistema operativo y el navegador actualizados.
- No ejecutes la app con documentos de origen desconocido en equipos sin
  antivirus.
- Guarda los expedientes en carpetas con acceso restringido.
- Verifica la integridad de las descargas (idealmente, usa los enlaces oficiales
  del repositorio).
