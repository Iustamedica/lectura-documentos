"""Interfaz de linea de comandos del extractor documental.

Comandos:

    documental procesar <carpeta> --json salidas/expediente.json
    documental revisor  <expediente.json> --html salidas/revision.html
    documental informe  <expediente.json> --docx salidas/informe.docx

Ejemplo completo para este expediente:

    .venv/bin/documental procesar ../../escaneos-csm \\
        --json salidas/expediente.json --render salidas/render \\
        --titulares caso.json
    # abrir salidas/revision.html en el navegador, corregir y descargar
    # expediente_corregido.json dentro de salidas/
    .venv/bin/documental informe salidas/expediente_corregido.json \\
        --docx salidas/informe.docx --render salidas/render
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .pipeline import PipelineOptions, process_folder, save_expediente
from .revisor import cargar_expediente, generar_revisor
from .report_docx import generar_informe
from .titulares import load_titulares


def _cmd_procesar(args: argparse.Namespace) -> int:
    carpeta = Path(args.carpeta)
    if not carpeta.exists():
        print(f"Error: la carpeta no existe: {carpeta}", file=sys.stderr)
        return 2
    config = load_titulares(Path(args.titulares)) if args.titulares else []
    options = PipelineOptions(
        render_dir=Path(args.render) if args.render else None,
        dpi=args.dpi,
        min_confidence=args.min_confidence,
    )
    print(f"Procesando {carpeta} (OCR local, puede tardar unos segundos por pagina)...")
    expediente = process_folder(carpeta, options=options, titulares_config=config)
    destino = save_expediente(expediente, Path(args.json))
    print(f"Documentos: {len(expediente.documentos)} | titulares: {len(expediente.titulares)}")
    for titular in expediente.titulares:
        print(f"  - {titular.rut or '(sin RUT)'}  {titular.nombre}  {titular.relacion}")
    if expediente.advertencias:
        print(f"Advertencias: {len(expediente.advertencias)} (ver anexo del informe)")
    print(f"JSON: {destino}")
    if args.html:
        html = generar_revisor(
            expediente,
            Path(args.html),
            image_rel_prefix=args.image_prefix,
        )
        print(f"Revisor: {html}")
    return 0


def _cmd_revisor(args: argparse.Namespace) -> int:
    expediente = cargar_expediente(Path(args.json))
    html = generar_revisor(expediente, Path(args.html), image_rel_prefix=args.image_prefix)
    print(f"Revisor generado: {html}")
    print("Abralo con doble clic, corrija los datos y use 'Exportar JSON corregido'.")
    return 0


def _cmd_informe(args: argparse.Namespace) -> int:
    expediente = cargar_expediente(Path(args.json))
    render = Path(args.render) if args.render else None
    destino = generar_informe(expediente, Path(args.docx), image_root=render)
    print(f"Informe Word: {destino}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="documental",
        description="Extrae datos de documentos escaneados y genera informe Word.",
    )
    sub = parser.add_subparsers(dest="comando", required=True)

    p_proc = sub.add_parser("procesar", help="Procesa una carpeta de PDF/imagenes")
    p_proc.add_argument("carpeta", help="Carpeta con los PDF o imagenes")
    p_proc.add_argument("--json", default="salidas/expediente.json", help="JSON de salida")
    p_proc.add_argument("--render", default="salidas/render", help="Carpeta de recortes PNG")
    p_proc.add_argument("--html", default="", help="Generar tambien el revisor HTML")
    p_proc.add_argument("--titulares", default="", help="JSON con titulares conocidos")
    p_proc.add_argument("--dpi", type=int, default=300, help="DPI de render del PDF")
    p_proc.add_argument(
        "--min-confidence", type=float, default=0.35, dest="min_confidence",
        help="Confianza minima del OCR para aceptar un token",
    )
    p_proc.add_argument(
        "--image-prefix", default="render/", dest="image_prefix",
        help="Ruta relativa de los recortes dentro del HTML",
    )
    p_proc.set_defaults(func=_cmd_procesar)

    p_rev = sub.add_parser("revisor", help="Genera revisor HTML desde un expediente JSON")
    p_rev.add_argument("json", help="Expediente JSON")
    p_rev.add_argument("--html", default="salidas/revision.html", help="HTML de salida")
    p_rev.add_argument("--image-prefix", default="render/", dest="image_prefix")
    p_rev.set_defaults(func=_cmd_revisor)

    p_inf = sub.add_parser("informe", help="Genera el informe Word")
    p_inf.add_argument("json", help="Expediente JSON (base o corregido)")
    p_inf.add_argument("--docx", default="salidas/informe.docx", help="Word de salida")
    p_inf.add_argument("--render", default="salidas/render", help="Carpeta de recortes PNG")
    p_inf.set_defaults(func=_cmd_informe)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
