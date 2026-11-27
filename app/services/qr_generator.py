# app/services/qr_generator.py
import qrcode
from pathlib import Path

def generar_qr_png(payload: str, destino: Path) -> Path:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=6, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    destino.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(destino))
    return destino
