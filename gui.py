import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core import (
    append_serial,
    load_serial_sets,
    next_sn_max_plus_one,
    next_sn_smallest_free,
    validate_serial,
)
from pdf_label import datamatrix_available, generate_label_pdf
from printing import print_pdf_lp, has_lp


CSV_PATH = "serials.csv"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Serial Label Tool")
        self.resizable(False, False)

        self.serial_var = tk.StringVar()
        self.note_var = tk.StringVar()
        self.printer_var = tk.StringVar()
        self.next_mode_var = tk.StringVar(value="max+1")
        self.crc_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Bitte Seriennummer eingeben.")
        self.dm_status_var = tk.StringVar(value=self._dm_status_text())

        self.current_payload = None
        self.current_sn = None
        self.current_u32 = None
        self.payloads = set()
        self.u32_set = set()

        self._build_ui()
        self._bind_events()
        self._reload_sets()
        self._focus_serial()

    def _build_ui(self):
        padding = {"padx": 10, "pady": 5}

        serial_frame = ttk.Frame(self)
        serial_frame.grid(row=0, column=0, sticky="ew", **padding)
        ttk.Label(serial_frame, text="Seriennummer").grid(row=0, column=0, sticky="w")
        self.serial_entry = ttk.Entry(serial_frame, textvariable=self.serial_var, width=40)
        self.serial_entry.grid(row=1, column=0, sticky="ew")

        crc_frame = ttk.Frame(self)
        crc_frame.grid(row=1, column=0, sticky="w", **padding)
        ttk.Checkbutton(crc_frame, text="CRC-16 im Barcode", variable=self.crc_var, command=self._validate_live).grid(
            row=0, column=0, sticky="w"
        )

        note_frame = ttk.Frame(self)
        note_frame.grid(row=2, column=0, sticky="ew", **padding)
        ttk.Label(note_frame, text="Notiz (optional)").grid(row=0, column=0, sticky="w")
        ttk.Entry(note_frame, textvariable=self.note_var, width=40).grid(row=1, column=0, sticky="ew")

        printer_frame = ttk.Frame(self)
        printer_frame.grid(row=3, column=0, sticky="ew", **padding)
        ttk.Label(printer_frame, text="Drucker (optional)").grid(row=0, column=0, sticky="w")
        ttk.Entry(printer_frame, textvariable=self.printer_var, width=40).grid(row=1, column=0, sticky="ew")

        next_frame = ttk.Frame(self)
        next_frame.grid(row=4, column=0, sticky="ew", **padding)
        ttk.Label(next_frame, text="Next-Modus").grid(row=0, column=0, sticky="w")
        self.next_mode_combo = ttk.Combobox(
            next_frame, textvariable=self.next_mode_var, values=["max+1", "kleinste frei"], state="readonly", width=20
        )
        self.next_mode_combo.grid(row=1, column=0, sticky="w")
        ttk.Button(next_frame, text="Next", command=self._on_next).grid(row=1, column=1, padx=8)

        status_frame = ttk.Frame(self)
        status_frame.grid(row=5, column=0, sticky="ew", **padding)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, foreground="#b00020")
        self.status_label.grid(row=0, column=0, sticky="w")
        self.dm_label = ttk.Label(status_frame, textvariable=self.dm_status_var, foreground="#555555")
        self.dm_label.grid(row=1, column=0, sticky="w")

        button_frame = ttk.Frame(self)
        button_frame.grid(row=6, column=0, sticky="ew", **padding)
        ttk.Button(button_frame, text="Pruefen", command=self._on_check).grid(row=0, column=0, padx=3)
        ttk.Button(button_frame, text="Speichern (CSV)", command=self._on_save).grid(row=0, column=1, padx=3)
        ttk.Button(button_frame, text="Etikett (PDF)", command=self._on_label).grid(row=0, column=2, padx=3)
        ttk.Button(button_frame, text="Drucken", command=self._on_print).grid(row=0, column=3, padx=3)

    def _bind_events(self):
        self.serial_entry.bind("<Return>", lambda _event: self._on_check())
        self.serial_entry.bind("<KeyRelease>", lambda _event: self._validate_live())

    def _focus_serial(self):
        self.serial_entry.focus_set()
        self.serial_entry.select_range(0, tk.END)

    def _set_status(self, ok, text):
        color = "#2b7a2b" if ok else "#b00020"
        self.status_label.configure(foreground=color)
        self.status_var.set(text)

    def _dm_status_text(self):
        if datamatrix_available():
            return "DataMatrix: verfuegbar"
        return "DataMatrix: nicht verfuegbar (Platzhalter im PDF)."

    def _reload_sets(self):
        self.payloads, self.u32_set = load_serial_sets(CSV_PATH)

    def _validate_live(self):
        result = validate_serial(self.serial_var.get(), CSV_PATH, self.crc_var.get())
        if result.ok:
            self.current_payload = result.payload
            self.current_sn = result.normalized
            self.current_u32 = result.u32_hex
            self._set_status(True, f"OK: {result.normalized} | u32={result.u32_hex} | payload={result.payload}")
        else:
            self.current_payload = result.payload
            self.current_sn = result.normalized
            self.current_u32 = result.u32_hex
            self._set_status(False, result.message)

    def _ensure_valid(self):
        self._validate_live()
        if not self.current_payload or not self.current_sn:
            messagebox.showerror("Fehler", "Seriennummer ungueltig oder unvollstaendig.")
            return False
        return True

    def _on_check(self):
        self._validate_live()
        self._focus_serial()

    def _on_save(self):
        if not self._ensure_valid():
            return
        try:
            append_serial(
                CSV_PATH,
                self.current_sn,
                self.current_payload,
                self.current_u32,
                self.note_var.get().strip(),
            )
        except Exception as exc:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen: {exc}")
            return
        self._reload_sets()
        self._set_status(True, "Gespeichert.")
        self._focus_serial()

    def _on_label(self):
        if not self._ensure_valid():
            return
        default_name = f"label_{self.current_payload}.pdf"
        path = filedialog.asksaveasfilename(
            title="Etikett speichern",
            defaultextension=".pdf",
            initialfile=default_name,
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        dm_info = {"available": False}
        try:
            generate_label_pdf(path, self.current_sn, self.current_payload, dm_info)
        except Exception as exc:
            messagebox.showerror("Fehler", f"PDF-Erzeugung fehlgeschlagen: {exc}")
            return
        if dm_info.get("available"):
            self._set_status(True, f"PDF erzeugt: {os.path.basename(path)}")
        else:
            self._set_status(True, f"PDF erzeugt (ohne DataMatrix): {os.path.basename(path)}")
        self._focus_serial()

    def _on_print(self):
        if not self._ensure_valid():
            return
        tmp_name = f"_tmp_label_{self.current_payload}.pdf"
        tmp_path = os.path.join(os.getcwd(), tmp_name)
        dm_info = {"available": False}
        try:
            generate_label_pdf(tmp_path, self.current_sn, self.current_payload, dm_info)
        except Exception as exc:
            messagebox.showerror("Fehler", f"PDF-Erzeugung fehlgeschlagen: {exc}")
            return
        if not has_lp():
            messagebox.showwarning("Warnung", f"lp nicht vorhanden. PDF bleibt liegen: {tmp_path}")
            self._set_status(False, f"lp fehlt. PDF: {tmp_path}")
            return
        ok, err = print_pdf_lp(tmp_path, self.printer_var.get().strip() or None)
        if ok:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            self._set_status(True, "Druckauftrag gesendet.")
        else:
            messagebox.showwarning("Warnung", f"Druck fehlgeschlagen: {err}\nPDF bleibt liegen: {tmp_path}")
            self._set_status(False, f"Druck fehlgeschlagen. PDF: {tmp_path}")
        self._focus_serial()

    def _on_next(self):
        self._reload_sets()
        try:
            if self.next_mode_var.get() == "kleinste frei":
                sn = next_sn_smallest_free(self.u32_set)
            else:
                sn = next_sn_max_plus_one(self.u32_set)
        except ValueError as exc:
            messagebox.showerror("Fehler", str(exc))
            return
        if not sn:
            messagebox.showerror("Fehler", "Konnte keine Seriennummer erzeugen.")
            return
        self.serial_var.set(sn)
        self._validate_live()
        self._focus_serial()


def run_app():
    app = App()
    app.mainloop()
