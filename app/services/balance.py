# app/services/balance.py
# Calculo del balance trimestral y de la hoja de trabajo del modelo 303 (IVA).
# Criterio: IVA devengado en la fecha de emision de la factura (regimen general, no criterio de caja).
import csv
from datetime import date
from pathlib import Path
from ..db.database import get_connection

TRIMESTRES = {1: ((1, 1), (3, 31)), 2: ((4, 1), (6, 30)), 3: ((7, 1), (9, 30)), 4: ((10, 1), (12, 31))}


def rango_trimestre(anio: int, trimestre: int):
    (m1, d1), (m2, d2) = TRIMESTRES[trimestre]
    return date(anio, m1, d1).isoformat(), date(anio, m2, d2).isoformat()


def plazo_presentacion(anio: int, trimestre: int) -> str:
    """Plazo general del modelo 303 (si vence en festivo/fin de semana pasa al siguiente dia habil)."""
    if trimestre == 1:
        return f"del 1 al 20 de abril de {anio}"
    if trimestre == 2:
        return f"del 1 al 20 de julio de {anio}"
    if trimestre == 3:
        return f"del 1 al 20 de octubre de {anio}"
    return f"del 1 al 30 de enero de {anio + 1}"


def _r(x):
    return round(float(x or 0), 2)


def calcular(anio: int, trimestre: int) -> dict:
    ini, fin = rango_trimestre(anio, trimestre)
    conn = get_connection()

    # --- Ingresos (facturas emitidas no anuladas)
    ing = conn.execute("""
        SELECT COUNT(*) n, COALESCE(SUM(base_imponible),0) base, COALESCE(SUM(total_iva),0) iva,
               COALESCE(SUM(total_factura),0) total, COALESCE(SUM(pendiente),0) pendiente
        FROM facturas WHERE estado='emitida' AND fecha_emision BETWEEN ? AND ?""", (ini, fin)).fetchone()
    anuladas = conn.execute("""SELECT COUNT(*) n FROM facturas WHERE estado='anulada'
                               AND fecha_emision BETWEEN ? AND ?""", (ini, fin)).fetchone()["n"]
    dev_rows = conn.execute("""
        SELECT d.porcentaje pct, SUM(d.base) base, SUM(d.cuota) cuota
        FROM desglose_iva_factura d JOIN facturas f ON f.id=d.factura_id
        WHERE f.estado='emitida' AND f.fecha_emision BETWEEN ? AND ?
        GROUP BY d.porcentaje ORDER BY d.porcentaje DESC""", (ini, fin)).fetchall()
    devengado = {r["pct"]: (_r(r["base"]), _r(r["cuota"])) for r in dev_rows}

    # --- Cobros del trimestre (por fecha de cobro)
    cob = conn.execute("""
        SELECT COALESCE(SUM(c.importe),0) total FROM cobros c JOIN facturas f ON f.id=c.factura_id
        WHERE f.estado='emitida' AND c.fecha_cobro BETWEEN ? AND ?""", (ini, fin)).fetchone()
    cobros_por_forma = conn.execute("""
        SELECT c.forma_pago forma, SUM(c.importe) total FROM cobros c JOIN facturas f ON f.id=c.factura_id
        WHERE f.estado='emitida' AND c.fecha_cobro BETWEEN ? AND ?
        GROUP BY c.forma_pago ORDER BY total DESC""", (ini, fin)).fetchall()

    # --- Gastos
    gas = conn.execute("""
        SELECT COUNT(*) n, COALESCE(SUM(base),0) base, COALESCE(SUM(cuota_iva),0) iva,
               COALESCE(SUM(total),0) total,
               COALESCE(SUM(CASE WHEN pagado=1 THEN total ELSE 0 END),0) pagado,
               COALESCE(SUM(CASE WHEN pagado=0 THEN total ELSE 0 END),0) por_pagar,
               COALESCE(SUM(CASE WHEN iva_deducible=1 THEN base ELSE 0 END),0) base_ded,
               COALESCE(SUM(CASE WHEN iva_deducible=1 THEN cuota_iva ELSE 0 END),0) cuota_ded,
               COALESCE(SUM(CASE WHEN iva_deducible=0 THEN cuota_iva ELSE 0 END),0) cuota_no_ded
        FROM gastos WHERE fecha BETWEEN ? AND ?""", (ini, fin)).fetchone()
    sop_rows = conn.execute("""
        SELECT porcentaje_iva pct, SUM(base) base, SUM(cuota_iva) cuota FROM gastos
        WHERE iva_deducible=1 AND fecha BETWEEN ? AND ? GROUP BY porcentaje_iva
        ORDER BY porcentaje_iva DESC""", (ini, fin)).fetchall()
    soportado = {r["pct"]: (_r(r["base"]), _r(r["cuota"])) for r in sop_rows}
    conn.close()

    cuota_dev = _r(sum(c for _, c in devengado.values()))
    cuota_ded = _r(gas["cuota_ded"])
    resultado_iva = _r(cuota_dev - cuota_ded)
    beneficio = _r(ing["base"] - gas["base"] - gas["cuota_no_ded"])
    return {
        "anio": anio, "trimestre": trimestre, "inicio": ini, "fin": fin,
        "plazo": plazo_presentacion(anio, trimestre),
        "ingresos": {"n": ing["n"], "base": _r(ing["base"]), "iva": _r(ing["iva"]), "total": _r(ing["total"]),
                     "pendiente_cobro": _r(ing["pendiente"]), "anuladas": anuladas},
        "devengado": devengado, "cuota_devengada": cuota_dev,
        "cobros": {"total": _r(cob["total"]),
                   "por_forma": [(r["forma"], _r(r["total"])) for r in cobros_por_forma]},
        "gastos": {"n": gas["n"], "base": _r(gas["base"]), "iva": _r(gas["iva"]), "total": _r(gas["total"]),
                   "pagado": _r(gas["pagado"]), "por_pagar": _r(gas["por_pagar"]),
                   "base_deducible": _r(gas["base_ded"]), "iva_no_deducible": _r(gas["cuota_no_ded"])},
        "soportado": soportado, "cuota_deducible": cuota_ded,
        "resultado_iva": resultado_iva, "beneficio": beneficio,
    }


# Casillas del modelo 303 (regimen general) para cada tipo. Referencia orientativa.
CASILLAS_DEVENGADO = {4.0: ("01", "02", "03"), 10.0: ("04", "05", "06"), 21.0: ("07", "08", "09")}


def filas_303(b: dict):
    """Lista de (casilla, concepto, importe) para la hoja de trabajo."""
    filas = []
    for pct, (c_base, c_tipo, c_cuota) in sorted(CASILLAS_DEVENGADO.items()):
        base, cuota = b["devengado"].get(pct, (0.0, 0.0))
        filas.append((c_base, f"Base imponible devengada al {pct:g}%", base))
        filas.append((c_cuota, f"Cuota devengada al {pct:g}%", cuota))
    otros = [(p, v) for p, v in b["devengado"].items() if p not in CASILLAS_DEVENGADO]
    for p, (base, cuota) in otros:
        filas.append(("—", f"Base al {p:g}% (revisar casilla en el formulario oficial)", base))
        if cuota:
            filas.append(("—", f"Cuota al {p:g}% (revisar casilla)", cuota))
    filas.append(("27", "TOTAL CUOTA DEVENGADA", b["cuota_devengada"]))
    filas.append(("28", "Base de operaciones interiores corrientes (soportado deducible)", b["gastos"]["base_deducible"]))
    filas.append(("29", "Cuota de operaciones interiores corrientes (soportado deducible)", b["cuota_deducible"]))
    filas.append(("45", "TOTAL A DEDUCIR", b["cuota_deducible"]))
    filas.append(("46", "RESULTADO RÉGIMEN GENERAL (27 − 45)", b["resultado_iva"]))
    filas.append(("69/71", "Resultado de la autoliquidación (sin otras regularizaciones)", b["resultado_iva"]))
    return filas


def exportar_csv(b: dict, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([f"Hoja de trabajo modelo 303 - {b['trimestre']}T {b['anio']}"])
        w.writerow(["Casilla", "Concepto", "Importe (EUR)"])
        for cas, conc, imp in filas_303(b):
            w.writerow([cas, conc, f"{imp:.2f}".replace(".", ",")])
        w.writerow([])
        w.writerow(["Aviso", "Referencia orientativa. Comprueba cada casilla en el formulario oficial de la AEAT."])
    return destino


def exportar_pdf(b: dict, empresa: dict, destino: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    destino.parent.mkdir(parents=True, exist_ok=True)
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(destino), pagesize=A4, leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    story = [Paragraph(f"Hoja de trabajo · Modelo 303 · {b['trimestre']}T {b['anio']}", st["Title"]),
             Paragraph(f"{empresa.get('nombre','')} — NIF {empresa.get('nif','')}", st["Normal"]),
             Paragraph(f"Periodo: {b['inicio']} a {b['fin']} · Plazo de presentación: {b['plazo']}", st["Normal"]),
             Spacer(1, 6*mm)]
    data = [["Casilla", "Concepto", "Importe"]]
    for cas, conc, imp in filas_303(b):
        data.append([cas, Paragraph(conc, st["Normal"]), f"{imp:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")])
    t = Table(data, colWidths=[22*mm, 120*mm, 35*mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 6*mm)]
    story.append(Paragraph(
        "Documento de apoyo generado por CD Factu. <b>No es una declaración presentada.</b> Las casillas son "
        "orientativas: copia los importes en el formulario oficial de la Sede electrónica de la AEAT "
        "(Modelo 303) y revisa regularizaciones, compensaciones de periodos anteriores y regímenes especiales.",
        st["Normal"]))
    doc.build(story)
    return destino


# ============================================================
# RESUMEN ANUAL: modelo 390 (IVA) + previsión orientativa de IRPF
# ============================================================

def plazo_anual(anio: int) -> str:
    """Plazo general de presentación del modelo 390."""
    return f"del 1 al 30 de enero de {anio + 1}"


def calcular_anual(anio: int, tipo_irpf: float = 20.0) -> dict:
    """Resumen anual de IVA y previsión orientativa de IRPF.

    El IRPF se estima con un tipo efectivo configurable sobre el rendimiento neto
    (facturación sin IVA − gastos − IVA no deducible), restando las retenciones
    que los clientes han practicado. Las retenciones practicadas a proveedores
    se muestran aparte: son una obligación distinta (modelo 111), no reducen
    la propia cuota del IRPF.
    """
    ini, fin = date(anio, 1, 1).isoformat(), date(anio, 12, 31).isoformat()
    conn = get_connection()

    ing = conn.execute("""
        SELECT COUNT(*) n, COALESCE(SUM(base_imponible),0) base, COALESCE(SUM(total_iva),0) iva,
               COALESCE(SUM(total_factura),0) total, COALESCE(SUM(retencion_irpf),0) retencion
        FROM facturas WHERE estado='emitida' AND fecha_emision BETWEEN ? AND ?""", (ini, fin)).fetchone()
    anuladas = conn.execute("""SELECT COUNT(*) n FROM facturas WHERE estado='anulada'
                               AND fecha_emision BETWEEN ? AND ?""", (ini, fin)).fetchone()["n"]
    dev_rows = conn.execute("""
        SELECT d.porcentaje pct, SUM(d.base) base, SUM(d.cuota) cuota
        FROM desglose_iva_factura d JOIN facturas f ON f.id=d.factura_id
        WHERE f.estado='emitida' AND f.fecha_emision BETWEEN ? AND ?
        GROUP BY d.porcentaje ORDER BY d.porcentaje DESC""", (ini, fin)).fetchall()
    devengado = {r["pct"]: (_r(r["base"]), _r(r["cuota"])) for r in dev_rows}
    cob = conn.execute("""
        SELECT COALESCE(SUM(c.importe),0) total FROM cobros c JOIN facturas f ON f.id=c.factura_id
        WHERE f.estado='emitida' AND c.fecha_cobro BETWEEN ? AND ?""", (ini, fin)).fetchone()

    gas = conn.execute("""
        SELECT COUNT(*) n, COALESCE(SUM(base),0) base, COALESCE(SUM(cuota_iva),0) iva,
               COALESCE(SUM(total),0) total, COALESCE(SUM(retencion_irpf),0) retencion,
               COALESCE(SUM(CASE WHEN iva_deducible=1 THEN base ELSE 0 END),0) base_ded,
               COALESCE(SUM(CASE WHEN iva_deducible=1 THEN cuota_iva ELSE 0 END),0) cuota_ded,
               COALESCE(SUM(CASE WHEN iva_deducible=0 THEN cuota_iva ELSE 0 END),0) cuota_no_ded,
               COALESCE(SUM(CASE WHEN pagado=1 THEN total ELSE 0 END),0) pagado,
               COALESCE(SUM(CASE WHEN pagado=0 THEN total ELSE 0 END),0) por_pagar
        FROM gastos WHERE fecha BETWEEN ? AND ?""", (ini, fin)).fetchone()
    sop_rows = conn.execute("""
        SELECT porcentaje_iva pct, SUM(base) base, SUM(cuota_iva) cuota FROM gastos
        WHERE iva_deducible=1 AND fecha BETWEEN ? AND ? GROUP BY porcentaje_iva
        ORDER BY porcentaje_iva DESC""", (ini, fin)).fetchall()
    soportado = {r["pct"]: (_r(r["base"]), _r(r["cuota"])) for r in sop_rows}
    conn.close()

    cuota_dev = _r(sum(c for _, c in devengado.values()))
    cuota_ded = _r(gas["cuota_ded"])
    resultado_iva = _r(cuota_dev - cuota_ded)

    base_ingresos = _r(ing["base"])
    iva_no_deducible = _r(gas["cuota_no_ded"])
    base_gastos = _r(_r(gas["base"]) + iva_no_deducible)
    rendimiento = _r(base_ingresos - base_gastos)
    tipo = round(float(tipo_irpf or 0), 2)
    cuota_estimada = _r(max(rendimiento, 0) * tipo / 100.0)
    ret_sufridas = _r(ing["retencion"])
    ret_practicadas = _r(gas["retencion"])
    saldo_irpf = _r(cuota_estimada - ret_sufridas)

    return {
        "anio": anio, "inicio": ini, "fin": fin, "plazo": plazo_anual(anio),
        "ingresos": {"n": ing["n"], "base": base_ingresos, "iva": _r(ing["iva"]),
                     "total": _r(ing["total"]), "retenciones": ret_sufridas, "anuladas": anuladas},
        "devengado": devengado, "cuota_devengada": cuota_dev,
        "cobros": {"total": _r(cob["total"])},
        "gastos": {"n": gas["n"], "base": _r(gas["base"]), "iva": _r(gas["iva"]),
                   "total": _r(gas["total"]), "base_deducible": _r(gas["base_ded"]),
                   "iva_no_deducible": iva_no_deducible, "retenciones": ret_practicadas,
                   "pagado": _r(gas["pagado"]), "por_pagar": _r(gas["por_pagar"])},
        "soportado": soportado, "cuota_deducible": cuota_ded,
        "resultado_iva": resultado_iva,
        "trimestres": [calcular(anio, t) for t in range(1, 5)],
        "irpf": {"tipo": tipo, "base_ingresos": base_ingresos, "base_gastos": base_gastos,
                 "rendimiento_neto": rendimiento, "cuota_estimada": cuota_estimada,
                 "retenciones_sufridas": ret_sufridas, "retenciones_practicadas": ret_practicadas,
                 "saldo": saldo_irpf},
    }


# Casillas del modelo 390 para régimen ordinario (referencia orientativa).
CASILLAS_390_DEVENGADO = {4.0: ("01", "02"), 10.0: ("03", "04"), 21.0: ("05", "06")}


def filas_390(b: dict):
    """Lista de (casilla, concepto, importe) para la hoja de trabajo del modelo 390."""
    filas = []
    for pct, (c_base, c_cuota) in sorted(CASILLAS_390_DEVENGADO.items()):
        base, cuota = b["devengado"].get(pct, (0.0, 0.0))
        filas.append((c_base, f"Base imponible devengada al {pct:g}% (régimen ordinario)", base))
        filas.append((c_cuota, f"Cuota devengada al {pct:g}% (régimen ordinario)", cuota))
    for pct, (base, cuota) in b["devengado"].items():
        if pct not in CASILLAS_390_DEVENGADO:
            filas.append(("—", f"Base al {pct:g}% (revisar casilla según ejercicio)", base))
            if cuota:
                filas.append(("—", f"Cuota al {pct:g}% (revisar casilla)", cuota))
    filas.append(("47", "Total cuotas de IVA devengadas", b["cuota_devengada"]))
    filas.append(("48", "Total bases deducibles · operaciones interiores corrientes",
                  b["gastos"]["base_deducible"]))
    filas.append(("49", "Total cuotas deducibles · operaciones interiores corrientes",
                  b["cuota_deducible"]))
    filas.append(("86", "Resultado del régimen general", b["resultado_iva"]))
    filas.append(("99", "Volumen de operaciones en régimen general (sin IVA)", b["ingresos"]["base"]))
    return filas


def exportar_csv_anual(b: dict, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow([f"Resumen anual IVA (modelo 390) - {b['anio']}"])
        w.writerow(["Casilla", "Concepto", "Importe (EUR)"])
        for cas, conc, imp in filas_390(b):
            w.writerow([cas, conc, f"{imp:.2f}".replace(".", ",")])
        w.writerow([])
        w.writerow(["Resumen trimestral", "Cuota devengada", "Cuota deducible", "Resultado"])
        for t in b["trimestres"]:
            w.writerow([f"{t['trimestre']}T", f"{t['cuota_devengada']:.2f}".replace(".", ","),
                        f"{t['cuota_deducible']:.2f}".replace(".", ","),
                        f"{t['resultado_iva']:.2f}".replace(".", ",")])
        w.writerow([])
        ir = b["irpf"]
        w.writerow(["Previsión IRPF (orientativa)", "Importe (EUR)"])
        for conc, imp in [("Tipo efectivo aplicado (%)", ir["tipo"]),
                          ("Facturación sin IVA", ir["base_ingresos"]),
                          ("Gastos + IVA no deducible", ir["base_gastos"]),
                          ("Rendimiento neto estimado", ir["rendimiento_neto"]),
                          ("Cuota IRPF estimada", ir["cuota_estimada"]),
                          ("− Retenciones sufridas", ir["retenciones_sufridas"]),
                          ("Saldo orientativo a pagar (+)", ir["saldo"])]:
            w.writerow([conc, f"{imp:.2f}".replace(".", ",")])
        w.writerow(["Retenciones practicadas a proveedores (informativo)",
                    f"{ir['retenciones_practicadas']:.2f}".replace(".", ",")])
        w.writerow([])
        w.writerow(["Aviso", "Hoja de trabajo orientativa. No es una declaración presentada. "
                             "Revisa las casillas en el formulario oficial y la previsión de IRPF con tu asesor."])
    return destino


def exportar_pdf_anual(b: dict, empresa: dict, destino: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    destino.parent.mkdir(parents=True, exist_ok=True)
    st = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(destino), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=15 * mm, bottomMargin=15 * mm)
    eur_str = lambda x: f"{x:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    story = [Paragraph(f"Resumen anual · Modelo 390 · {b['anio']}", st["Title"]),
             Paragraph(f"{empresa.get('nombre','')} — NIF {empresa.get('nif','')}", st["Normal"]),
             Paragraph(f"Periodo: {b['inicio']} a {b['fin']} · Plazo 390: {b['plazo']}", st["Normal"]),
             Spacer(1, 6 * mm), Paragraph("<b>IVA — hoja de trabajo del modelo 390</b>", st["Normal"])]
    data = [["Casilla", "Concepto", "Importe"]]
    for cas, conc, imp in filas_390(b):
        data.append([cas, Paragraph(conc, st["Normal"]), eur_str(imp)])
    t = Table(data, colWidths=[22 * mm, 120 * mm, 35 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("ALIGN", (2, 0), (2, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    story += [t, Spacer(1, 6 * mm)]

    story.append(Paragraph("<b>Desglose trimestral del IVA</b>", st["Normal"]))
    data = [["Trimestre", "Cuota devengada", "Cuota deducible", "Resultado"]]
    for r in b["trimestres"]:
        data.append([f"{r['trimestre']}T", eur_str(r["cuota_devengada"]),
                     eur_str(r["cuota_deducible"]), eur_str(r["resultado_iva"])])
    t2 = Table(data, colWidths=[35 * mm, 47 * mm, 47 * mm, 48 * mm])
    t2.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                            ("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
    story += [t2, Spacer(1, 6 * mm)]

    ir = b["irpf"]
    story.append(Paragraph("<b>Previsión orientativa de IRPF</b>", st["Normal"]))
    data = [["Concepto", "Importe"]]
    for conc, imp in [("Tipo efectivo aplicado", f"{ir['tipo']:g} %"),
                      ("Facturación sin IVA", eur_str(ir["base_ingresos"])),
                      ("Gastos + IVA no deducible", eur_str(ir["base_gastos"])),
                      ("Rendimiento neto estimado", eur_str(ir["rendimiento_neto"])),
                      ("Cuota IRPF estimada", eur_str(ir["cuota_estimada"])),
                      ("− Retenciones sufridas", eur_str(ir["retenciones_sufridas"])),
                      ("Saldo orientativo a pagar (+)", eur_str(ir["saldo"])),
                      ("Retenciones practicadas a proveedores (informativo)",
                       eur_str(ir["retenciones_practicadas"]))]:
        data.append([conc, imp])
    t3 = Table(data, colWidths=[120 * mm, 57 * mm])
    t3.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT")]))
    story += [t3, Spacer(1, 6 * mm)]
    story.append(Paragraph(
        "Documento de apoyo generado por CD Factu. <b>No es una declaración presentada ni un asesoramiento fiscal.</b> "
        "Las casillas del 390 son orientativas: comprueba el ejercicio y copia los importes en el formulario oficial "
        "de la AEAT. La previsión de IRPF usa un tipo efectivo simplificado: la cuota real depende de la escala "
        "de tu Comunidad Autónoma, situación personal, reducciones y regímenes especiales. Las retenciones "
        "practicadas a proveedores se declaran por separado (modelo 111) y no reducen tu IRPF.", st["Normal"]))
    doc.build(story)
    return destino
