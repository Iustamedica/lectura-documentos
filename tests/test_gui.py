"""Pruebas basicas de la mini app (sin abrir la ventana)."""

from pathlib import Path

from documental import gui


def test_main_es_llamable():
    assert callable(gui.main)


def test_carpeta_inicial_es_una_ruta():
    assert isinstance(gui._carpeta_inicial(), Path)


def test_escritor_de_cola_envia_texto():
    import queue

    cola: queue.Queue = queue.Queue()
    escritor = gui._EscritorCola(cola)
    assert escritor.write("hola") == 4
    assert cola.get_nowait() == ("texto", "hola")
    assert escritor.flush() is None
