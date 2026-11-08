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

from .categorias import CATEGORIAS, cargar_prestadores
from .compilar import CALIDAD_JPEG, DPI_COMPRESION, compilar
from .individualizacion import agrupar, escribir_csv, escribir_docx
from .ingesta import DPI_CONVERSION, preparar
from .ocr import TARGET_HEIGHT
from .organizar import (
    agrupar_refinado,
    escribir_indice_csv,
    escribir_indice_docx,
    escribir_leeme,
    ordenar,
)
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


def _cmd_ordenar(args: argparse.Namespace) -> int:
    expediente = cargar_expediente(Path(args.json))
    if not expediente.documentos:
        print("Error: el expediente no tiene documentos.", file=sys.stderr)
        return 2
    if not args.origen:
        print(
            "Error: indique donde estan los archivos originales con --origen.",
            file=sys.stderr,
        )
        return 2

    prestadores = cargar_prestadores(Path(args.prestadores) if args.prestadores else None)
    grupos = agrupar_refinado(expediente.documentos, prestadores)
    if not grupos:
        print("Error: no se pudo agrupar ningun documento.", file=sys.stderr)
        return 2

    destino = Path(args.destino)
    resultado = ordenar(
        grupos,
        origen=[Path(ruta) for ruta in args.origen],
        destino=destino,
        estampar=not args.sin_estampar,
        comprimir=args.comprimir,
        dpi=args.dpi,
        calidad=args.calidad,
        prestadores=prestadores,
        dry_run=args.dry_run,
    )

    modo = " (simulacion: no se escribio nada)" if args.dry_run else ""
    print(f"Documentos: {resultado.documentos} | paginas: {resultado.paginas}{modo}")
    for clave, etiqueta, carpeta in CATEGORIAS:
        total = resultado.por_categoria.get(clave, 0)
        if total:
            print(f"  {carpeta:16s} {total:4d}  {etiqueta}")
    if resultado.por_prestador:
        print("Fichas por prestador:")
        for prestador, total in sorted(
            resultado.por_prestador.items(), key=lambda par: -par[1]
        ):
            print(f"  {total:4d}  {prestador}")
    if resultado.sin_prestador:
        print(
            f"AVISO: {resultado.sin_prestador} ficha(s) sin prestador identificado",
            file=sys.stderr,
        )
    if resultado.sin_clasificar:
        print(
            f"AVISO: {resultado.sin_clasificar} documento(s) sin clasificar",
            file=sys.stderr,
        )
    if resultado.compartidas:
        print(
            f"AVISO: {len(resultado.compartidas)} hoja(s) con mas de un documento "
            "(se repiten, una vez por documento)",
            file=sys.stderr,
        )
    for faltante in resultado.faltantes[:10]:
        print(f"AVISO: no se encontro el original: {faltante}", file=sys.stderr)

    if args.dry_run:
        return 0

    print(f"Indice CSV: {escribir_indice_csv(grupos, destino / 'indice.csv')}")
    print(f"Indice Word: {escribir_indice_docx(grupos, destino / 'indice.docx')}")
    print(f"Manifiesto: {escribir_leeme(resultado, destino / 'LEEME.txt', origen=args.origen)}")
    save_expediente(expediente, destino / "expediente-refinado.json")
    print(f"Carpeta ordenada: {destino} ({resultado.bytes / (1024 * 1024):.1f} MB)")
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
    destino = generar_informe(
        expediente,
        Path(args.docx),
        image_root=render,
        incluir_imagenes=args.con_imagenes,
    )
    print(f"Informe Word: {destino}")
    return 0


def _abrir_salidas(carpeta: Path, html: Path, docx: Path) -> None:
    """Abre (best-effort) la carpeta de resultados, el revisor y el Word."""
    import platform
    import subprocess
    import webbrowser

    try:
        webbrowser.open(html.resolve().as_uri())
    except Exception:
        pass
    sistema = platform.system()
    for objetivo in (carpeta, docx):
        try:
            if sistema == "Darwin":
                subprocess.Popen(["open", str(objetivo)])
            elif sistema == "Windows":
                subprocess.Popen(["cmd", "/c", "start", "", str(objetivo)])
            else:
                subprocess.Popen(["xdg-open", str(objetivo)])
        except Exception:
            pass


def _cmd_expediente(args: argparse.Namespace) -> int:
    """Proceso completo y simple: carpeta de documentos -> revisor + Word.

    Crea la estructura de trabajo (``1. Documentos a procesar`` y ``Resultados``),
    procesa todo lo que haya (PDF e imagenes), y deja la primera version editable
    (revisor HTML) junto al informe Word.
    """
    from datetime import datetime

    base = Path(args.carpeta)
    base.mkdir(parents=True, exist_ok=True)
    entrada = base / "1. Documentos a procesar"
    resultados = base / "Resultados"
    entrada.mkdir(exist_ok=True)
    resultados.mkdir(exist_ok=True)

    guia = entrada / "LEEME - aqui van los documentos.txt"
    if not guia.exists():
        guia.write_text(
            "Coloque en esta carpeta TODAS las fotos (JPG/PNG) y PDF del expediente.\n"
            "Pueden ser muchos archivos. Idealmente, escaneos derechos y legibles.\n"
            "Luego ejecute 'Procesar documentos' (doble clic).\n",
            encoding="utf-8",
        )

    sufijos = {".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    archivos = [p for p in entrada.iterdir() if p.is_file() and p.suffix.lower() in sufijos]
    if archivos:
        entrada_real = entrada
    else:
        sueltos = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in sufijos]
        if not sueltos:
            print(
                f"No hay documentos para procesar. Copie sus archivos en:\n  {entrada}",
                file=sys.stderr,
            )
            return 2
        entrada_real = base

    render = resultados / "render"
    json_path = resultados / "expediente.json"
    html_path = resultados / "Revision.html"
    docx_path = resultados / "Informe.docx"

    titulares: list = []
    caso = Path(args.caso) if getattr(args, "caso", "") else (base / "caso.json")
    if caso.is_file():
        titulares = load_titulares(caso)

    options = PipelineOptions(
        render_dir=render,
        dpi=300,
        min_confidence=0.35,
        target_height=TARGET_HEIGHT,
    )

    print("Paso 1 de 3: leyendo documentos (OCR local; puede tardar unos segundos por pagina)...")
    expediente = process_folder(entrada_real, options=options, titulares_config=titulares)
    save_expediente(expediente, json_path)
    print(f"   Documentos: {len(expediente.documentos)} | titulares: {len(expediente.titulares)}")

    print("Paso 2 de 3: generando la revision para corregir...")
    generar_revisor(expediente, html_path, image_rel_prefix="render/")

    print("Paso 3 de 3: generando el informe Word...")
    generar_informe(expediente, docx_path, image_root=render, incluir_imagenes=False)

    documentos_dir = None
    if getattr(args, "ordenar", False):
        try:
            print("   (extra) agrupando documentos por categoria en Resultados/Documentos ...")
            prestadores = cargar_prestadores(None)
            grupos = agrupar_refinado(expediente.documentos, prestadores)
            documentos_dir = resultados / "Documentos"
            ordenar(
                grupos,
                origen=[entrada_real],
                destino=documentos_dir,
                estampar=True,
                comprimir=False,
                prestadores=prestadores,
                dry_run=False,
            )
        except Exception as error:  # no debe romper el proceso principal
            print(f"   (aviso) no se pudo ordenar automaticamente: {error}", file=sys.stderr)
            documentos_dir = None

    registro = resultados / "Registro.txt"
    with registro.open("w", encoding="utf-8") as fh:
        fh.write(f"Proceso terminado: {datetime.now().isoformat(timespec='seconds')}\n")
        fh.write(f"Entrada: {entrada_real}\n")
        fh.write(f"Documentos detectados: {len(expediente.documentos)}\n")
        fh.write(f"Titulares: {len(expediente.titulares)}\n")
        fh.write(f"Advertencias: {len(expediente.advertencias)}\n\n")
        fh.write("ARCHIVOS GENERADOS:\n")
        fh.write(f"  - {html_path}  (abrir en el navegador para revisar/corregir)\n")
        fh.write(f"  - {docx_path}  (informe Word)\n")
        fh.write(f"  - {json_path}\n")
        if documentos_dir:
            fh.write(f"  - {documentos_dir}  (un PDF por documento, por categoria)\n")

    print()
    print(f"LISTO. Resultados en: {resultados}")
    print(f"  Revision (revisar y corregir): {html_path.name}")
    print(f"  Informe Word:                  {docx_path.name}")
    if documentos_dir:
        print(f"  Documentos ordenados:          {documentos_dir.name}/")

    if getattr(args, "abrir", False):
        _abrir_salidas(resultados, html_path, docx_path)
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
    p_inf.add_argument(
        "--con-imagenes", action="store_true", dest="con_imagenes",
        help="Incluir los recortes de imagen en el Word (por defecto no: el PDF ya los tiene)",
    )
    p_inf.set_defaults(func=_cmd_informe)

    p_ord = sub.add_parser(
        "ordenar",
        help="Agrupa los documentos por categoria en una carpeta (un PDF por documento)",
    )
    p_ord.add_argument("json", help="Expediente JSON")
    p_ord.add_argument(
        "--origen", action="append", default=[], metavar="CARPETA",
        help="Carpeta con los archivos originales (se puede repetir)",
    )
    p_ord.add_argument(
        "--destino", default="V.1", help="Carpeta de salida (por defecto V.1)"
    )
    p_ord.add_argument(
        "--prestadores", default="",
        help="JSON con la tabla de prestadores para agrupar las fichas",
    )
    p_ord.add_argument(
        "--sin-estampar", action="store_true", dest="sin_estampar",
        help="No agrega el encabezado de identificacion a cada documento",
    )
    p_ord.add_argument(
        "--comprimir", action="store_true",
        help="Recomprime las imagenes de los PDF consolidados por categoria",
    )
    p_ord.add_argument(
        "--dpi", type=int, default=DPI_COMPRESION,
        help=f"DPI objetivo al comprimir (por defecto {DPI_COMPRESION})",
    )
    p_ord.add_argument(
        "--calidad", type=int, default=CALIDAD_JPEG,
        help=f"Calidad JPEG al comprimir, 0-100 (por defecto {CALIDAD_JPEG})",
    )
    p_ord.add_argument(
        "--dry-run", action="store_true", dest="dry_run",
        help="No escribe nada; solo informa como quedaria la carpeta",
    )
    p_ord.set_defaults(func=_cmd_ordenar)

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

    p_exp = sub.add_parser(
        "expediente",
        help="Proceso completo: carpeta de documentos -> revision editable + Word",
        description=(
            "Toma una carpeta con fotos y PDF, crea la estructura de trabajo "
            "('1. Documentos a procesar' y 'Resultados'), procesa todo y deja el "
            "revisor HTML y el informe Word. Pensado para uso simple (doble clic)."
        ),
    )
    p_exp.add_argument(
        "--carpeta", default=".",
        help="Carpeta de trabajo donde estan los documentos (por defecto el directorio actual)",
    )
    p_exp.add_argument(
        "--caso", default="",
        help="Archivo caso.json con titulares conocidos (opcional; por defecto busca caso.json en la carpeta)",
    )
    p_exp.add_argument(
        "--ordenar", action="store_true",
        help="Ademas, agrupa los documentos por categoria en Resultados/Documentos",
    )
    p_exp.add_argument(
        "--abrir", action="store_true",
        help="Abre la carpeta de resultados, el revisor y el Word al terminar",
    )
    p_exp.set_defaults(func=_cmd_expediente)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
