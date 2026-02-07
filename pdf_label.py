import os
import tempfile

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


DM_AVAILABLE = True
try:
    from pystrich.datamatrix import DataMatrixEncoder
except Exception:
    DM_AVAILABLE = False


def datamatrix_available():
    return DM_AVAILABLE


def _render_datamatrix_png(payload):
    if not DM_AVAILABLE:
        return None
    tmp = tempfile.NamedTemporaryFile(prefix="dm_", suffix=".png", delete=False)
    tmp_path = tmp.name
    tmp.close()
    try:
        DataMatrixEncoder(payload).save(tmp_path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return None
    return tmp_path


def generate_label_pdf(output_path, normalized_serial, payload, dm_available_out=None):
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    label_w_mm = 54.0
    label_h_mm = 17.0
    width = label_w_mm * mm
    height = label_h_mm * mm

    c = canvas.Canvas(output_path, pagesize=(width, height))
    c.setTitle(f"Label {normalized_serial}")

    margin = 1.5 * mm
    gap = 2.0 * mm
    dm_size = height - 2 * margin
    dm_x = width - margin - dm_size
    dm_y = margin

    text_x = margin
    text_right = dm_x - gap
    max_text_width = max(1, text_right - text_x)

    font_name = "Helvetica-Bold"
    font_size = 12.0
    while font_size > 8.0:
        if c.stringWidth(normalized_serial, font_name, font_size) <= max_text_width:
            break
        font_size -= 0.5
    font_size = max(font_size, 8.0)
    c.setFont(font_name, font_size)
    text_height_mm = font_size * 0.3528 * mm
    y = (height - text_height_mm) / 2
    c.drawString(text_x, y, normalized_serial)
    dm_png_path = _render_datamatrix_png(payload)
    if dm_available_out is not None:
        dm_available_out["available"] = dm_png_path is not None
    if dm_png_path is not None:
        c.drawImage(dm_png_path, dm_x, dm_y, width=dm_size, height=dm_size, preserveAspectRatio=True, mask="auto")
    else:
        c.rect(dm_x, dm_y, dm_size, dm_size, stroke=1, fill=0)
        c.setFont("Helvetica", 5.5)
        c.drawString(dm_x + 1.2 * mm, dm_y + dm_size / 2 - 1.2 * mm, "DataMatrix fehlt")

    c.showPage()
    c.save()
    if dm_png_path is not None:
        try:
            os.remove(dm_png_path)
        except OSError:
            pass
