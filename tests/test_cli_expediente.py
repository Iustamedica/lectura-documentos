"""Pruebas del comando unico `expediente` (sin ejecutar OCR)."""

from pathlib import Path

from documental.cli import build_parser, main


def test_parser_incluye_expediente():
    parser = build_parser()
    args = parser.parse_args(["expediente", "--carpeta", "."])
    assert args.func.__name__ == "_cmd_expediente"
    assert args.carpeta == "."
    assert args.ordenar is False
    assert args.abrir is False


def test_expediente_crea_estructura_y_avisa_si_no_hay_documentos(tmp_path: Path):
    rc = main(["expediente", "--carpeta", str(tmp_path)])
    # Sin documentos debe avisar y devolver 2 (no romper)
    assert rc == 2
    assert (tmp_path / "1. Documentos a procesar").is_dir()
    assert (tmp_path / "Resultados").is_dir()
    guia = tmp_path / "1. Documentos a procesar" / "LEEME - aqui van los documentos.txt"
    assert guia.is_file()


def test_expediente_parser_tiene_compresion():
    parser = build_parser()
    args = parser.parse_args(["expediente", "--comprimir"])
    assert args.comprimir is True
    assert args.dpi > 0
    assert 0 <= args.calidad <= 100

