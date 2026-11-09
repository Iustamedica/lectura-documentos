# Perfil legal (v1)

El motor de la herramienta es el mismo para todos los dominios. Un **perfil**
define *qué documentos conoce*, *cómo los clasifica*, *qué datos extrae* y *cómo
los ordena*. El perfil `salud` es el histórico (bonos, fichas, recetas); este
documento describe el perfil `legal`.

Uso:

```bash
documental expediente --perfil legal --carpeta "Mi expediente" --ordenar
documental clasificar "Carpeta con PDF" --perfil legal --csv inventario.csv
```

Sin `--perfil`, la herramienta usa **salud** (comportamiento de siempre).

## Alcance v1

Expediente judicial chileno (civil, laboral, penal y familia): escritos,
resoluciones, notificaciones, contratos, comprobantes, poderes, certificados,
informes y peritajes. Fuera de alcance: tributario y contencioso administrativo
(caen en `08-otros`).

## Categorías (carpetas de salida)

| # | Carpeta | Contenido |
|---|---|---|
| 01 | `01-escritos` | Escritos de parte (demanda, contestación, recursos, solicitudes). |
| 02 | `02-resoluciones` | Proveídos, autos, sentencias, actas, certificados del tribunal. |
| 03 | `03-notificaciones` | Cédulas y notificaciones electrónicas. |
| 04 | `04-contratos` | Contratos y anexos. |
| 05 | `05-comprobantes` | Boletas, facturas, transferencias, pagos. |
| 06 | `06-poderes-certificados` | Poderes, mandatos, personería, certificados, cédulas. |
| 07 | `07-informes-peritajes` | Peritajes, tasaciones, informes técnicos y sociales. |
| 08 | `08-otros` | Oficios, cartas, correos, pagarés, cheques, sin clasificar. |

## Tipos canónicos

**Escritos:** Demanda, Contestación de la demanda, Réplica, Dúplica, Recurso de
apelación, Recurso de casación, Recurso de reposición, Recurso de queja, Escrito
de prueba, Alegato, Desistimiento o allanamiento, Escrito.

**Resoluciones:** Sentencia definitiva, Auto o sentencia interlocutoria, Auto de
prueba, Proveído, Acta de audiencia, Certificado del tribunal.

**Notificaciones:** Cédula de notificación, Notificación electrónica.

**Contratos:** Contrato de arriendo, de trabajo, de compraventa, de prestación de
servicios, de mutuo, Contrato (genérico).

**Comprobantes:** Boleta electrónica, Factura electrónica, Boleta de honorarios,
Comprobante de transferencia o depósito, Comprobante de pago.

**Poderes y certificados:** Poder notarial, Mandato judicial, Certificado de
nacimiento, de matrimonio, de antecedentes, de vigencia o personería, Cédula de
identidad o pasaporte, Certificado (genérico).

**Informes:** Informe pericial, Tasación, Informe técnico o social.

**Penal (v0.3):** Querella, Denuncia, Formalización de la investigación,
Acusación fiscal, Sobreseimiento, Sentencia condenatoria, Sentencia absolutoria,
Medida cautelar.

**Familia (v0.3):** Demanda de divorcio, Demanda de alimentos, Demanda de
cuidado personal, Demanda de relación directa y regular, Medida de protección
(VIF).

**Otros:** Oficio, Carta o correo, Acta de mediación, Pagaré, Cheque, Documento
sin clasificar.

## Campos

Comunes (ya existentes): `tipo_documento`, `folio`, `emisor_nombre`,
`emisor_rut`, `fecha_emision`, `monto_total`, `observaciones`, `items`.

Propios del perfil legal (en `Document.extra`):

| Campo | Ejemplo | Crítico |
|---|---|---|
| `rol` | `C-1234-2025` | Sí |
| `tribunal` | `2° Juzgado Civil de Santiago` | Sí |
| `caratula` | `Pérez Soto con Banco X` | Sí |
| `parte_demandante` | `Juan Pérez Soto` | No |
| `parte_demandada` | `Banco X S.A.` | No |
| `tipo_parte` | `tribunal` / `demandante` / `demandado` | No |
| `materia` | `Civil` / `Laboral` / `Ejecutivo` | No |
| `cuaderno` | `Principal` / `Incidental` / `Ejecución` | No |
| `fojas` | `12` | No |
| `etapa` | `discusión` / `prueba` / `sentencia` | No |
| `abogado_patrocinante` | nombre | No |
| `abogado_apoderado` | nombre | No |
| `notaria` | `Notaría 5ª Santiago` | No |
| `repertorio` | `1234` | No |
| `fecha_notificacion` | `12-03-2025` | No |
| `forma_notificacion` | `Personal` / `Electrónica` / `Por aviso` | No |
| `monto_demanda` | `1250000` | No |
| `monto_condena` | `1250000` | No |
| `moneda` | `CLP` / `UF` / `USD` | No |
| `sociedad` | razón social | No |
| `giro` | giro comercial | No |

## Campos críticos por tipo

El semáforo no exige los mismos campos a todos los documentos: un contrato no
tiene ROL y una notificación no tiene monto.

| Categoría | Campos críticos |
|---|---|
| Escritos | `rol`, `tribunal`, `caratula` |
| Resoluciones | `rol`, `tribunal`, `fecha_emision` |
| Notificaciones | `rol`, `fecha_notificacion`, `forma_notificacion` |
| Contratos | `fecha_emision` |
| Comprobantes | `fecha_emision`, `monto_total`, `emisor_rut` |
| Poderes y certificados | `fecha_emision`, `notaria` |
| Informes y peritajes | `fecha_emision` |
| Otros | `fecha_emision` |

## Individualización

- Una hoja es un documento; se separa solo si hay **folios distintos**.
- Se unen hojas consecutivas del mismo archivo, misma categoría, mismo tipo y
  sin conflicto de **folio ni ROL**.
- Orden cronológico por fecha; sin fecha legible, al final.
- El índice incluye: N, categoría, tipo, fecha, ROL, tribunal, carátula, parte,
  folio y elementos de individualización.

## Salidas

```
Resultados/
  Revision.html          revisor para corregir
  Informe.docx           informe con portada (ROL/carátula), resumen por
                         categoría, índice y fichas por documento
  expediente.json        datos crudos
  Documentos/            (con --ordenar) un PDF por documento, por categoría
  01-escritos/ ...
  indice.csv / indice.docx
  LEEME.txt
```

## Límites

| Caso | Resultado esperado |
|---|---|
| PDF del Poder Judicial con texto | Excelente (sin OCR). |
| Escaneo derecho y legible | Bueno. |
| Escaneo torcido o fotos | Regular; revisar. |
| Manuscrito | Bajo; revisar siempre. |
| Timbres, sellos y firmas | No se extraen. |
