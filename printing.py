import shutil
import subprocess


def has_lp():
    return bool(shutil.which("lp"))


def print_pdf_lp(path, printer_name=None):
    if not has_lp():
        return False, "lp nicht vorhanden"
    cmd = ["lp"]
    if printer_name:
        cmd += ["-d", printer_name]
    cmd += [path]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        return False, (result.stderr or "lp Fehler").strip()
    return True, ""
