"""Mini app de escritorio para usar la herramienta sin terminal ni GitHub.

Doble clic, se elige la carpeta del expediente, el modo (judicial o salud) y se
presiona "Procesar". El OCR y el informe corren en este mismo computador.
"""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path


def _base_dir() -> Path:
    """Carpeta de la aplicacion (junto al .exe cuando esta empaquetada)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _carpeta_inicial() -> Path:
    candidata = _base_dir() / "Expediente"
    if candidata.exists():
        return candidata
    return Path.home() / "Expediente"


class _EscritorCola:
    """Reemplaza stdout/stderr para llevar el progreso a la ventana."""

    def __init__(self, cola: queue.Queue) -> None:
        self.cola = cola

    def write(self, texto: str) -> int:
        if texto:
            self.cola.put(("texto", texto))
        return len(texto)

    def flush(self) -> None:
        return None


class Ventana:
    def __init__(self, root) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext, ttk

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.root = root
        self.cola: queue.Queue = queue.Queue()
        self.resultados: Path | None = None
        self.procesando = False

        root.title("Lector de documentos")
        root.geometry("820x620")
        root.minsize(720, 520)

        marco = ttk.Frame(root, padding=16)
        marco.pack(fill="both", expand=True)

        ttk.Label(
            marco, text="Lector de documentos", font=("Segoe UI", 17, "bold")
        ).pack(anchor="w")

        ttk.Label(
            marco,
            text=(
                "Convierte fotos y PDF de un expediente en un borrador editable y un "
                "informe Word.\nTodo se procesa en este computador: no se sube nada a internet."
            ),
            justify="left",
        ).pack(anchor="w", pady=(4, 12))

        fila = ttk.Frame(marco)
        fila.pack(fill="x")
        ttk.Label(fila, text="Carpeta del expediente:").pack(side="left")
        self.var_carpeta = tk.StringVar(value=str(_carpeta_inicial()))
        ttk.Entry(fila, textvariable=self.var_carpeta).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(fila, text="Elegir carpeta...", command=self.elegir_carpeta).pack(
            side="left"
        )

        modo = ttk.LabelFrame(marco, text="Tipo de documentos", padding=10)
        modo.pack(fill="x", pady=12)
        self.var_perfil = tk.StringVar(value="legal")
        ttk.Radiobutton(
            modo,
            text="Judicial (escritos, resoluciones, contratos, prueba)",
            variable=self.var_perfil,
            value="legal",
        ).pack(anchor="w")
        ttk.Radiobutton(
            modo,
            text="Salud (bonos, fichas, recetas, boletas)",
            variable=self.var_perfil,
            value="salud",
        ).pack(anchor="w")

        self.var_ordenar = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            marco,
            text="Ademas, ordenar por categoria y comprimir para el Poder Judicial",
            variable=self.var_ordenar,
        ).pack(anchor="w")

        acciones = ttk.Frame(marco)
        acciones.pack(fill="x", pady=12)
        self.boton_procesar = ttk.Button(
            acciones, text="Procesar documentos", command=self.procesar
        )
        self.boton_procesar.pack(side="left")
        self.boton_abrir = ttk.Button(
            acciones,
            text="Abrir resultados",
            command=self.abrir_resultados,
            state="disabled",
        )
        self.boton_abrir.pack(side="left", padx=8)
        self.boton_corregir = ttk.Button(
            acciones,
            text="Actualizar informe con correcciones",
            command=self.actualizar_corregido,
        )
        self.boton_corregir.pack(side="left", padx=8)

        self.progreso = ttk.Progressbar(marco, mode="indeterminate")
        self.progreso.pack(fill="x", pady=(0, 8))

        ttk.Label(marco, text="Progreso:").pack(anchor="w")
        self.registro = scrolledtext.ScrolledText(
            marco, height=14, wrap="word", state="disabled", font=("Consolas", 9)
        )
        self.registro.pack(fill="both", expand=True, pady=(4, 0))

        ttk.Label(
            marco,
            text=(
                "Licencia PolyForm Internal Use 1.0.0: uso interno gratuito; "
                "no distribuir ni revender."
            ),
            foreground="#666666",
        ).pack(anchor="w", pady=(8, 0))

        self._actualizar_modo()
        self.var_carpeta.trace_add("write", lambda *_: self._actualizar_modo())

    # ------------------------------------------------------------------
    def _actualizar_modo(self) -> None:
        """Preselecciona salud si la carpeta ya es de ese flujo."""
        from .perfiles.config import perfil_de_carpeta

        detectado = perfil_de_carpeta(self.var_carpeta.get())
        if detectado in ("salud", "legal"):
            self.var_perfil.set(detectado)

    def elegir_carpeta(self) -> None:
        elegida = self.filedialog.askdirectory(
            initialdir=self.var_carpeta.get() or str(Path.home()),
            title="Elija la carpeta del expediente",
        )
        if elegida:
            self.var_carpeta.set(elegida)
            self._actualizar_modo()

    def _append(self, texto: str) -> None:
        self.registro.configure(state="normal")
        self.registro.insert("end", texto)
        self.registro.see("end")
        self.registro.configure(state="disabled")

    def procesar(self) -> None:
        if self.procesando:
            return
        carpeta = Path(self.var_carpeta.get()).expanduser()
        if not str(carpeta).strip():
            self.messagebox.showwarning(
                "Falta la carpeta", "Elija la carpeta del expediente."
            )
            return
        self.resultados = carpeta / "Resultados"
        self.registro.configure(state="normal")
        self.registro.delete("1.0", "end")
        self.registro.configure(state="disabled")
        self._append(f"Procesando: {carpeta}\nModo: {self.var_perfil.get()}\n\n")

        argumentos = [
            "expediente",
            "--carpeta",
            str(carpeta),
            "--perfil",
            self.var_perfil.get(),
        ]
        if self.var_ordenar.get():
            argumentos += ["--ordenar", "--comprimir"]

        self.procesando = False
        self._lanzar(argumentos)

    def _lanzar(self, argumentos: list[str]) -> None:
        """Ejecuta un comando en segundo plano y bloquea los botones."""
        if self.procesando:
            return
        self.procesando = True
        self.boton_procesar.configure(state="disabled")
        self.boton_corregir.configure(state="disabled")
        self.boton_abrir.configure(state="disabled")
        self.progreso.start(12)
        hilo = threading.Thread(target=self._trabajar, args=(argumentos,), daemon=True)
        hilo.start()
        self.root.after(120, self._revisar_cola)

    def actualizar_corregido(self) -> None:
        """Regenera el informe Word desde el JSON corregido en el revisor."""
        if self.procesando:
            return
        inicial = self.resultados or (
            Path(self.var_carpeta.get()).expanduser() / "Resultados"
        )
        archivo = self.filedialog.askopenfilename(
            title="Elija el expediente_corregido.json exportado del revisor",
            initialdir=str(inicial) if inicial.exists() else str(Path.home()),
            filetypes=[("Expediente corregido", "*.json"), ("Todos", "*.*")],
        )
        if not archivo:
            return
        ruta = Path(archivo)
        destino = ruta.parent / "Informe-corregido.docx"
        self.resultados = ruta.parent
        self.registro.configure(state="normal")
        self.registro.delete("1.0", "end")
        self.registro.configure(state="disabled")
        self._append(f"Regenerando informe desde: {archivo}\n\n")
        self._lanzar(
            [
                "informe",
                archivo,
                "--docx",
                str(destino),
                "--perfil",
                self.var_perfil.get(),
            ]
        )

    # ------------------------------------------------------------------
    def _trabajar(self, argumentos: list[str]) -> None:
        salida, error = sys.stdout, sys.stderr
        escritor = _EscritorCola(self.cola)
        sys.stdout = sys.stderr = escritor
        codigo = 1
        try:
            from .cli import main

            codigo = int(main(argumentos) or 0)
        except SystemExit as exc:
            codigo = int(exc.code or 0)
        except Exception as exc:  # la ventana nunca debe cerrarse por un error
            self.cola.put(("texto", f"\nERROR: {exc}\n"))
            codigo = 1
        finally:
            sys.stdout, sys.stderr = salida, error
        self.cola.put(("fin", codigo))

    def _revisar_cola(self) -> None:
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "texto":
                    self._append(str(dato))
                elif tipo == "fin":
                    self._terminar(int(dato))
                    return
        except queue.Empty:
            pass
        self.root.after(120, self._revisar_cola)

    def _terminar(self, codigo: int) -> None:
        self.procesando = False
        self.progreso.stop()
        self.boton_procesar.configure(state="normal")
        self.boton_corregir.configure(state="normal")
        if codigo == 0:
            self.boton_abrir.configure(state="normal")
            self._append("\nLISTO. Revise Revision.html e Informe.docx en Resultados.\n")
            self.messagebox.showinfo(
                "Proceso terminado",
                "Los resultados quedaron en la carpeta 'Resultados'.\n\n"
                "Abra Revision.html para revisar y corregir los datos.",
            )
        else:
            self._append("\nEl proceso termino con errores. Revise el detalle arriba.\n")
            self.messagebox.showwarning(
                "Proceso con errores",
                "Revise el detalle en la ventana. Si el problema persiste, "
                "consulte el archivo Registro.txt de la carpeta Resultados.",
            )

    def abrir_resultados(self) -> None:
        import os
        import subprocess

        if self.resultados is None or not self.resultados.exists():
            self.messagebox.showinfo(
                "Sin resultados", "Todavia no hay una carpeta de resultados."
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(self.resultados))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(self.resultados)])
            else:
                subprocess.Popen(["xdg-open", str(self.resultados)])
        except Exception:
            self.messagebox.showinfo("Resultados", str(self.resultados))


def main() -> int:
    """Abre la ventana principal."""
    try:
        import tkinter as tk
    except ImportError:
        print(
            "No se encontro Tkinter. En Linux instale 'python3-tk' y vuelva a intentar.",
            file=sys.stderr,
        )
        return 1
    raiz = tk.Tk()
    Ventana(raiz)
    raiz.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


