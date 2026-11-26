# app/services/hash_chain.py
import hashlib, json
from datetime import date

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

def qr_payload_url(numero, nif_emisor, hash_registro) -> str:
    # URL de validación AEAT (Verifactu). En modalidad local se genera el mismo formato
    # para que el QR sea verificable si se remite posteriormente.
    return (f"https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR?"
            f"nif={nif_emisor}&numserie={numero}&fecha=&hash={hash_registro[:16]}")
