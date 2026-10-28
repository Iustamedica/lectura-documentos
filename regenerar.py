"""Regenera revisor HTML e informe Word desde un expediente.json ya calculado.

Sirve para aplicar cambios en la logica de agrupacion de titulares sin repetir
el OCR (que es la parte lenta). Reconstruye la lista de titulares a partir de los
documentos guardados y vuelve a escribir el JSON, el revisor y el Word.

Uso:
    python regenerar.py salidas/expediente.json --titulares caso.json \
        --html salidas/revision.html --docx salidas/informe.docx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from documental.pipeline import _completar_desde_config, save_expediente  # noqa: E402
from documental.report_docx import generar_informe  # noqa: E402
from documental.revisor import cargar_expediente, generar_revisor  # noqa: E402
from documental.titulares import load_titulares, resolve_expediente  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json", help="Expediente JSON generado por el pipeline")
    parser.add_argument("--titulares", default="", help="JSON con titulares conocidos")
    parser.add_argument("--html", default="", help="Salida del revisor HTML")
    parser.add_argument("--docx", default="", help="Salida del informe Word")
    parser.add_argument("--render", default="", help="Carpeta de recortes PNG")
    args = parser.parse_args(argv)

    ruta_json = Path(args.json)
    expediente = cargar_expediente(ruta_json)
    config = load_titulares(Path(args.titulares)) if args.titulares else []

    # Reagrupa titulares con la logica vigente y reescribe el JSON.
    expediente = resolve_expediente(
        expediente.documentos, expediente.carpeta, expediente.generado, config
    )
    _completar_desde_config(expediente, config)
    save_expediente(expediente, ruta_json)

    print(f"Documentos: {len(expediente.documentos)} | titulares: {len(expediente.titulares)}")
    for titular in expediente.titulares:
        rut = titular.rut or "(sin RUT)"
        print(f"  - {rut}  {titular.nombre}  {titular.relacion}")

    if args.html:
        destino = Path(args.html)
        generar_revisor(expediente, destino, image_rel_prefix="render/")
        print(f"Revisor: {destino}")

    if args.docx:
        destino = Path(args.docx)
        generar_informe(
            expediente, destino, image_root=Path(args.render) if args.render else None
        )
        print(f"Informe: {destino}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
