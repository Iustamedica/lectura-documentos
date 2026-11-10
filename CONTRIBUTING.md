# Cómo contribuir

Gracias por querer mejorar la herramienta. Este proyecto es pequeño y prioriza
la **estabilidad del OCR**, la **claridad para usuarios no técnicos** y la
**privacidad de los expedientes**.

## Antes de programar

1. Abre un *issue* describiendo el problema o la mejora.
2. Espera una respuesta para evitar trabajo duplicado.
3. No incluyas documentos reales, nombres, RUT ni rutas con datos de clientes.

## Entorno de desarrollo

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
PYTHONPATH=src .venv/bin/python -m pytest -q
```

En Windows:

```bat
py -3.11 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
set PYTHONPATH=src
.venv\Scripts\python -m pytest -q
```

## Qué se espera de un cambio

- **Pruebas**: agrega o ajusta tests en `tests/`. La suite debe quedar verde.
- **Sin datos reales**: usa nombres, RUT y montos ficticios.
- **Compatibilidad**: no cambies el comportamiento del perfil `salud` salvo que
  el issue lo pida; es el flujo histórico.
- **Estilo**: Python 3.10+, tipado cuando aporta claridad, comentarios en español
  y funciones pequeñas.
- **Dependencias**: evita agregar bibliotecas nuevas si la estándar alcanza.
  Cualquier dependencia nueva debe justificarse en el issue.

## Empaquetado

Si tocas el empaquetado o los lanzadores:

```bash
bash empaquetar/empaquetar_linux.sh     # Linux
empaquetar\empaquetar_windows.bat       # Windows
```

Verifica que el paquete incluya `rapidocr/models/*.onnx`, `revisor_template.html`
y `LICENSE`.

## Licencia de las contribuciones

Al enviar un *pull request* aceptas que:

1. Tu aporte se licencia bajo la **PolyForm Internal Use License 1.0.0**.
2. Autorizas al mantenedor a **relicenciar** el proyecto (incluido tu aporte) para
   otros usos, incluida la distribución comercial.

Si tu aporte incorpora código de terceros, decláralo y adjunta su licencia.

## Reportes de seguridad

No uses *issues* públicos para vulnerabilidades. Sigue
[`SECURITY.md`](SECURITY.md).
