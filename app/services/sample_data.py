# app/services/sample_data.py
from ..db.database import get_connection
from ..services.hash_chain import hash_registro_factura, qr_payload_url
from ..models.factura import Factura, LineaFactura
from datetime import date, timedelta
import os

def seed_sample_data() -> str:
    conn = get_connection()
    # Empresa
    emp = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
    if not (emp and emp["nombre"]):
        conn.execute("""UPDATE empresa SET nombre=?, nif=?, direccion=?, cp=?, ciudad=?,
                        comunidad_autonoma=?, pais=?, actualizado_en=datetime('now','localtime') WHERE id=1""",
                    ("CD Factu Ejemplo S.L.", "B76543214", "Calle Ejemplo 1", "28001", "Madrid",
                     "Madrid", "España"))
    # Tipos IVA ya existen por defecto

    # Clientes
    if conn.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"] == 0:
        clientes = [
            ("Juan", "García López", None, "12345678Z", "Calle Mayor 1", "28001", "Madrid", "Madrid"),
            ("María", "Pérez Ruiz", "Pérez y Asociados", "B12345674", "Av. de la Paz 5", "28002", "Madrid", "Madrid"),
            ("Carlos", "Sánchez", None, "98765432M", "Plaza España 3", "41001", "Sevilla", "Andalucía"),
        ]
        for c in clientes:
            conn.execute("""INSERT INTO clientes (nombre, apellidos, empresa, dni_cif, direccion, cp, ciudad,
                            comunidad_autonoma, pais) VALUES (?,?,?,?,?,?,?,?,?)""",
                         (c[0], c[1], c[2], c[3], c[4], c[5], c[6], c[7], "España"))

    # Productos
    if conn.execute("SELECT COUNT(*) c FROM productos").fetchone()["c"] == 0:
        # tipo iva 21
        t21 = conn.execute("SELECT id FROM tipos_iva WHERE porcentaje=21").fetchone()["id"]
        t10 = conn.execute("SELECT id FROM tipos_iva WHERE porcentaje=10").fetchone()["id"]
        prods = [
            ("P001", "Servicio de consultoría", 50.0, t21),
            ("P002", "Producto A", 25.0, t21),
            ("P003", "Producto B", 12.5, t10),
            ("P004", "Mantenimiento", 30.0, t21),
        ]
        for p in prods:
            conn.execute("""INSERT INTO productos (referencia, nombre, importe_base, tipo_iva_id) VALUES (?,?,?,?)""",
                         (p[0], p[1], p[2], p[3]))

    # Servicio de ejemplo
    if conn.execute("SELECT COUNT(*) c FROM servicios").fetchone()["c"] == 0:
        t21 = conn.execute("SELECT id FROM tipos_iva WHERE porcentaje=21").fetchone()["id"]
        conn.execute("""INSERT INTO servicios (titulo, descripcion, importe_base, tipo_iva_id) VALUES (?,?,?,?)""",
                     ("Informe pericial",
                      "Informe pericial de tercero encargado por el Juzgado de Murcia, sección de Primera Instancia, "
                      "sobre la valoración de una serie de daños producidos en su inmueble.", 450.0, t21))

    # Gastos de ejemplo (para el balance trimestral)
    if conn.execute("SELECT COUNT(*) c FROM gastos").fetchone()["c"] == 0:
        hoy = date.today().isoformat()
        for prov, nif, base, pct, ret_pct in [("Papelería Central S.L.", "B12345674", 80.0, 21.0, 0.0),
                                              ("Gestoría Ejemplo", "B76543214", 120.0, 21.0, 15.0),
                                              ("Librería Técnica", "B12345674", 45.0, 4.0, 0.0)]:
            cuota = round(base * pct / 100.0, 2)
            total = round(base + cuota, 2)
            ret = round(base * ret_pct / 100.0, 2)
            conn.execute("""INSERT INTO gastos (fecha, proveedor, nif_proveedor, concepto, base, porcentaje_iva,
                            cuota_iva, total, retencion_irpf, iva_deducible, pagado) VALUES (?,?,?,?,?,?,?,?,?,1,1)""",
                         (hoy, prov, nif, "Gasto de ejemplo", base, pct, cuota, total, ret))

    # Facturas de ejemplo (solo si no hay)
    if conn.execute("SELECT COUNT(*) c FROM facturas").fetchone()["c"] == 0:
        emp = conn.execute("SELECT nif FROM empresa WHERE id=1").fetchone()
        nif_emisor = emp["nif"] if emp else ""
        clientes = conn.execute("SELECT id, dni_cif FROM clientes ORDER BY id").fetchall()
        prod_rows = conn.execute("SELECT id, nombre, importe_base, tipo_iva_id FROM productos ORDER BY id").fetchall()
        # map iva pct
        def iva_pct(tid):
            r = conn.execute("SELECT porcentaje FROM tipos_iva WHERE id=?", (tid,)).fetchone()
            return r["porcentaje"] if r else 21.0

        # Factura 1: 2 líneas, parcialmente cobrada
        c1 = clientes[0]
        lineas1 = [
            (prod_rows[0]["id"], prod_rows[0]["nombre"], 1, float(prod_rows[0]["importe_base"]), iva_pct(prod_rows[0]["tipo_iva_id"]), prod_rows[0]["tipo_iva_id"]),
            (prod_rows[1]["id"], prod_rows[1]["nombre"], 2, float(prod_rows[1]["importe_base"]), iva_pct(prod_rows[1]["tipo_iva_id"]), prod_rows[1]["tipo_iva_id"]),
        ]
        _crear_factura(conn, "2026-000001", date.today().isoformat(), c1["id"], c1["dni_cif"] or "",
                       nif_emisor, lineas1, estado_cobro_inicial="parcial", importe_cobro=40.0,
                       retencion_pct=15.0)
        # Factura 2: pagada
        c2 = clientes[1]
        lineas2 = [
            (prod_rows[2]["id"], prod_rows[2]["nombre"], 3, float(prod_rows[2]["importe_base"]), iva_pct(prod_rows[2]["tipo_iva_id"]), prod_rows[2]["tipo_iva_id"]),
        ]
        _crear_factura(conn, "2026-000002", (date.today() - timedelta(days=5)).isoformat(), c2["id"],
                       c2["dni_cif"] or "", nif_emisor, lineas2, estado_cobro_inicial="pagada")

    conn.commit()
    conn.close()
    return "Datos de ejemplo cargados. Todo correcto."

def _crear_factura(conn, numero, fecha, cliente_id, nif_receptor, nif_emisor, lineas,
                   estado_cobro_inicial="no_cobrada", importe_cobro=None, retencion_pct=0.0):
    # calcular totales
    base_total = 0.0
    iva_total = 0.0
    lineas_calc = []
    for (pid, concepto, cant, base, pct, tid) in lineas:
        base_linea = round(cant * base, 2)
        iva_linea = round(base_linea * pct / 100.0, 2)
        total_linea = round(base_linea + iva_linea, 2)
        base_total = round(base_total + base_linea, 2)
        iva_total = round(iva_total + iva_linea, 2)
        lineas_calc.append((pid, concepto, cant, base, pct, tid, base_linea, iva_linea, total_linea))
    total_factura = round(base_total + iva_total, 2)
    retencion = round(base_total * (retencion_pct or 0) / 100.0, 2)
    a_cobrar = round(total_factura - retencion, 2)
    # hash
    last = conn.execute("SELECT hash_registro FROM registros_facturacion ORDER BY id DESC LIMIT 1").fetchone()
    hash_anterior = last["hash_registro"] if last else None
    hash_reg = hash_registro_factura(numero, fecha, nif_emisor, nif_receptor, base_total, total_factura, hash_anterior)
    qr_payload = qr_payload_url(numero, nif_emisor, fecha, total_factura, False)
    # insert factura
    cur = conn.execute("""INSERT INTO facturas (numero, fecha_emision, cliente_id, base_imponible, total_iva,
                          total_factura, retencion_irpf, estado, estado_cobro, pendiente, hash_registro, hash_anterior)
                          VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (numero, fecha, cliente_id, base_total, iva_total, total_factura, retencion, "emitida",
                        "no_cobrada", a_cobrar, hash_reg, hash_anterior))
    fid = cur.lastrowid
    for i, (pid, concepto, cant, base, pct, tid, bl, il, tl) in enumerate(lineas_calc):
        conn.execute("""INSERT INTO lineas_factura (factura_id, orden, producto_id, concepto, cantidad,
                        importe_base, tipo_iva_id, porcentaje_iva, base_linea, iva_linea, total_linea)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                     (fid, i, pid, concepto, cant, base, tid, pct, bl, il, tl))
    # desglose
    desg = {}
    for (pid, concepto, cant, base, pct, tid, bl, il, tl) in lineas_calc:
        if pct not in desg:
            desg[pct] = [0.0, 0.0, tid]
        desg[pct][0] = round(desg[pct][0] + bl, 2)
        desg[pct][1] = round(desg[pct][1] + il, 2)
    for pct, (b, c, tid) in desg.items():
        conn.execute("""INSERT INTO desglose_iva_factura (factura_id, tipo_iva_id, porcentaje, base, cuota)
                        VALUES (?,?,?,?,?)""", (fid, tid, pct, b, c))
    # registro
    conn.execute("""INSERT INTO registros_facturacion (factura_id, tipo, numero_factura, fecha_emision,
                    nif_emisor, nif_receptor, base_imponible, total_factura, hash_registro,
                    hash_anterior, qr_payload) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                 (fid, "alta", numero, fecha, nif_emisor, nif_receptor, base_total, total_factura,
                  hash_reg, hash_anterior, qr_payload))
    # cobro
    if estado_cobro_inicial == "pagada":
        conn.execute("""INSERT INTO cobros (factura_id, fecha_cobro, importe, forma_pago) VALUES (?,?,?,?)""",
                     (fid, fecha, a_cobrar, "Transferencia"))
        conn.execute("UPDATE facturas SET estado_cobro='pagada', pendiente=0 WHERE id=?", (fid,))
    elif estado_cobro_inicial == "parcial":
        imp = importe_cobro if importe_cobro is not None else round(a_cobrar / 2, 2)
        conn.execute("""INSERT INTO cobros (factura_id, fecha_cobro, importe, forma_pago) VALUES (?,?,?,?)""",
                     (fid, fecha, imp, "Transferencia"))
        pend = round(a_cobrar - imp, 2)
        conn.execute("UPDATE facturas SET estado_cobro=?, pendiente=? WHERE id=?",
                     ("parcial" if pend > 0 else "pagada", max(pend, 0), fid))
    return fid
