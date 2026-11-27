# app/services/hash_chain.py
import hashlib, json
from datetime import date
from urllib.parse import quote

def sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def hash_registro_factura(numero, fecha_emision, nif_emisor, nif_receptor,
                        base_imponible, total_factura, hash_anterior=None) -> str:
    # Cadena canónica (orden estable) para el hash encadenado
    payload = {
        "numero": numero,
        "fecha": fecha_emision,
        "nif_emisor": nif_emisor,
        "nif_receptor": nif_receptor or "",
        "base": f"{base_imponible:.2f}",
        "total": f"{total_factura:.2f}",
        "hash_anterior": hash_anterior or "",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256_hex(canonical)

def _fecha_qr(fecha_emision: str) -> str:
    # ISO YYYY-MM-DD -> DD-MM-AAAA (formato exigido por AEAT)
    try:
        y, m, d = fecha_emision.split("-")
        return f"{d}-{m}-{y}"
    except Exception:
        return fecha_emision

def qr_payload_url(numero, nif_emisor, fecha_emision, total_factura,
                   verificable: bool = False) -> str:
    """URL de validación AEAT (Verifactu) según especificación técnica vigente.

    Contiene únicamente los 4 parámetros obligatorios: nif, numserie, fecha, importe.
    - nif: NIF del obligado a expedir la factura (9 chars)
    - numserie: número de serie + número de factura (max 60, ASCII 32-126, URL-encoded)
    - fecha: fecha de expedición en formato DD-MM-AAAA
    - importe: importe total con punto decimal (max 12 enteros + 2 decimales)

    El hash del registro NO forma parte del QR (especificación AEAT).
    El endpoint depende de si el sistema es VERI*FACTU (verificable) o no.
    """
    base = ("https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR"
            if verificable else
            "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQRNoVerifactu")
    params = [
        ("nif", nif_emisor or ""),
        ("numserie", numero or ""),
        ("fecha", _fecha_qr(fecha_emision)),
        ("importe", f"{float(total_factura):.2f}"),
    ]
    query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params)
    return f"{base}?{query}"
