"""Interfaz de linea de comandos del extractor documental.

Comandos:

    documental preparar   <carpeta_fotos> --destino salidas/pdf
    documental procesar   <carpeta> --json salidas/expediente.json
    documental revisor    <expediente.json> --html salidas/revision.html
    documental informe    <expediente.json> --docx salidas/informe.docx
    documental compilar   <expediente.json> --origen <carpeta_pdf>
                          --pdf salidas/documentos.pdf
                          --csv salidas/individualizacion.csv
                          --docx salidas/individualizacion.docx

Flujo completo cuando los documentos llegan como fotos de celular:

    .venv/bin/documental preparar ../../escaneos-postqx \\
        --destino salidas/pdf --unir-por-tiempo 35
    .venv/bin/documental procesar salidas/pdf \\
        --json salidas/expediente.json --render salidas/render \\
        --titulares caso.json --html salidas/revision.html
    # abrir salidas/revision.html, corregir y descargar expediente_corregido.json
    .venv/bin/documental compilar salidas/expediente_corregido.json \\
        --origen salidas/pdf --pdf salidas/documentos.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .compilar import CALIDAD_JPEG, DPI_COMPRESION, compilar
from .individualizacion import agrupar, escribir_csv, escribir_docx
from .ingesta import DPI_CONVERSION, preparar
from .ocr import TARGET_HEIGHT
from .pipeline import PipelineOptions, process_folder, save_expediente
from .revisor import cargar_expediente, generar_revisor
from .report_docx import generar_informe
from .titulares import load_titulares


def _cmd_preparar(args: argparse.Namespace) -> int:
    origen = Path(args.carpeta)
    if not origen.is_dir():
        print(f"Error: la carpeta no existe: {origen}", file=sys.stderr)
        return 2
    try:
        resultado = preparar(
            origen,
            Path(args.destino),
            unir_por_tiempo=args.unir_por_tiempo,
            dpi=args.dpi,
            dry_run=args.dry_run,
            forzar=args.forzar,
        )
    except (NotADirectoryError, FileExistsError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2

    modo = " (simulacion: no se escribio nada)" if resultado.dry_run else ""
    print(
        f"Imagenes: {resultado.total_imagenes} | "
        f"PDF resultantes: {resultado.total_pdfs}{modo}"
    )
    agrupados = [grupo for grupo in resultado.grupos if len(grupo) > 1]
    if agrupados:
        print(f"Grupos de varias hojas: {len(agrupados)}")
        for grupo in agrupados[:10]:
            print(f"  - {grupo[0].name} .. {grupo[-1].name} ({len(grupo)} hojas)")
        if len(agrupados) > 10:
            print(f"  ... y {len(agrupados) - 10} grupos mas")
    if args.mapa:
        print(f"Mapa foto -> PDF: {resultado.escribir_mapa(Path(args.mapa))}")
    if not resultado.dry_run:
        print(f"PDF en: {resultado.destino}")
    return 0


def _cmd_compilar(args: argparse.Namespace) -> int:
    expediente = cargar_expediente(Path(args.json))
    grupos = agrupar(expediente.documentos)
    if not grupos:
        print("Error: el expediente no tiene documentos.", file=sys.stderr)
        return 2
    if not args.origen:
        print(
            "Error: indique donde estan los archivos originales con --origen.",
            file=sys.stderr,
        )
        return 2

    resultado = compilar(
        grupos,
        origen=[Path(ruta) for ruta in args.origen],
        destino=Path(args.pdf),
        estampar=not args.sin_estampar,
        comprimir=args.comprimir,
        dpi=args.dpi,
        calidad=args.calidad,
        dry_run=args.dry_run,
    )
    modo = " (simulacion: sin PDF)" if args.dry_run else ""
    print(f"Documentos individualizados: {len(grupos)}{modo}")
    print(f"Compilados: {resultado.documentos} | paginas en el PDF: {resultado.paginas}")
    if resultado.faltantes:
        print(
            f"AVISO: {len(resultado.faltantes)} archivos no encontrados:",
            file=sys.stderr,
        )
        for nombre in resultado.faltantes[:10]:
            print(f"  - {nombre}", file=sys.stderr)
    if resultado.grupos_sin_paginas:
        print(
            "AVISO: documentos sin paginas validas: "
            + ", ".join(str(numero) for numero in resultado.grupos_sin_paginas),
            file=sys.stderr,
        )
    if resultado.paginas_compartidas:
        print(
            "AVISO: hojas con mas de un documento (se repiten en el PDF, una vez "
            "por cada documento):",
            file=sys.stderr,
        )
        for llave in resultado.paginas_compartidas[:10]:
            print(f"  - {llave}", file=sys.stderr)
    if args.csv:
        print(f"Individualizacion CSV: {escribir_csv(grupos, Path(args.csv))}")
    if args.docx:
        print(f"Individualizacion Word: {escribir_docx(grupos, Path(args.docx))}")
    if not resultado.dry_run:
        megas = resultado.bytes / (1024 * 1024)
        extra = f" | comprimido a {args.dpi} dpi (q{args.calidad})" if resultado.comprimido else ""
        print(f"PDF unico: {resultado.destino} ({megas:.1f} MB{extra})")
    return 0


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
        target_height=args.target_height,
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

    p_prep = sub.add_parser("preparar", help="Convierte fotos (JPG/PNG/TIFF) en PDF")
    p_prep.add_argument("carpeta", help="Carpeta con las fotos o imagenes")
    p_prep.add_argument(
        "--destino", default="salidas/pdf", help="Carpeta de los PDF generados"
    )
    p_prep.add_argument(
        "--unir-por-tiempo", type=int, default=0, dest="unir_por_tiempo",
        metavar="SEGUNDOS",
        help="Une fotos tomadas con menos de N segundos de diferencia (0 desactiva)",
    )
    p_prep.add_argument(
        "--dpi", type=int, default=DPI_CONVERSION,
        help="DPI asumido para pasar de pixeles a tamano de pagina (sin reducir)",
    )
    p_prep.add_argument(
        "--mapa", default="salidas/mapa_fotos.csv",
        help="CSV de trazabilidad foto -> PDF (cadena vacia para no escribirlo)",
    )
    p_prep.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="Muestra el plan sin escribir ningun archivo",
    )
    p_prep.add_argument(
        "--forzar", action="store_true",
        help="Permite escribir en una carpeta destino que ya tiene archivos",
    )
    p_prep.set_defaults(func=_cmd_preparar)

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
        "--target-height", type=int, default=TARGET_HEIGHT, dest="target_height",
        metavar="PIXELES",
        help="Alto al que se normaliza la imagen antes del OCR (reduce fotos de celular)",
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

    p_comp = sub.add_parser(
        "compilar", help="PDF unico con encabezados y tabla de individualizacion"
    )
    p_comp.add_argument("json", help="Expediente JSON (idealmente el corregido)")
    p_comp.add_argument(
        "--origen", action="append", default=[], metavar="CARPETA",
        help="Carpeta con los archivos originales (se puede repetir)",
    )
    p_comp.add_argument("--pdf", default="salidas/documentos.pdf", help="PDF unico de salida")
    p_comp.add_argument(
        "--csv", default="salidas/individualizacion.csv", help="Tabla de individualizacion (CSV)"
    )
    p_comp.add_argument(
        "--docx", default="salidas/individualizacion.docx", help="Tabla de individualizacion (Word)"
    )
    p_comp.add_argument(
        "--sin-estampar", action="store_true", dest="sin_estampar",
        help="Compila sin el encabezado de identificacion",
    )
    p_comp.add_argument(
        "--comprimir", action="store_true",
        help="Recomprime las imagenes (JPEG) para reducir el peso del PDF",
    )
    p_comp.add_argument(
        "--dpi", type=int, default=DPI_COMPRESION,
        help=f"DPI objetivo al comprimir (por defecto {DPI_COMPRESION})",
    )
    p_comp.add_argument(
        "--calidad", type=int, default=CALIDAD_JPEG,
        help=f"Calidad JPEG al comprimir, 0-100 (por defecto {CALIDAD_JPEG})",
    )
    p_comp.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="No escribe el PDF; solo informa y genera la tabla",
    )
    p_comp.set_defaults(func=_cmd_compilar)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
