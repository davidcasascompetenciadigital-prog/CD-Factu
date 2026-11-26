# app/services/verifactu_export.py
# Exportación de registros de facturación a XML/CSV para el asesor.
# Modalidad NO-Verifactu: no se envía a AEAT automáticamente.
import csv, sqlite3
from pathlib import Path
from ..db.database import get_connection

def exportar_csv(destino: Path) -> Path:
    conn = get_connection()
    rows = conn.execute("""
        SELECT r.numero_factura, r.fecha_emision, r.nif_emisor, r.nif_receptor,
               r.base_imponible, r.total_factura, r.hash_registro, r.hash_anterior,
               r.fecha_generacion, r.qr_payload
        FROM registros_facturacion r ORDER BY r.id
    """).fetchall()
    conn.close()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Numero", "Fecha", "NIF Emisor", "NIF Receptor", "Base", "Total",
                    "Hash", "Hash Anterior", "Generado", "QR Payload"])
        for r in rows:
            w.writerow(list(r))
    return destino
