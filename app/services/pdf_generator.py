# app/services/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os
from xml.sax.saxutils import escape

def _estilos():
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], fontSize=18, spaceAfter=6)
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=11, leading=14)
    return title, normal

def _concepto_paragraph(concepto, estilo):
    """Primera linea = titulo (negrita); el resto = descripcion, con saltos de linea."""
    partes = (concepto or "").split("\n", 1)
    html = f"<b>{escape(partes[0])}</b>"
    if len(partes) > 1 and partes[1].strip():
        html += "<br/>" + escape(partes[1].strip()).replace("\n", "<br/>")
    return Paragraph(html, estilo)

def _bloque_factura(story, factura, empresa, cliente, lineas, desglose, qr_path, title, normal, leyenda_qr=None):
    # Cabecera empresa
    if empresa.logo_path and os.path.exists(empresa.logo_path):
        story.append(Image(empresa.logo_path, width=40*mm, height=20*mm))
    story.append(Paragraph(f"<b>{empresa.nombre}</b>", title))
    story.append(Paragraph(f"NIF: {empresa.nif}", normal))
    story.append(Paragraph(f"{empresa.direccion}, {empresa.cp} {empresa.ciudad}", normal))
    story.append(Paragraph(f"{empresa.comunidad_autonoma}, {empresa.pais}", normal))
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph(f"<b>FACTURA Nº {factura.numero}</b>", title))
    story.append(Paragraph(f"Fecha: {factura.fecha_emision}", normal))
    story.append(Spacer(1, 4*mm))

    # Cliente
    story.append(Paragraph("<b>Cliente:</b>", normal))
    nombre_cli = cliente.nombre_mostrar() if hasattr(cliente, "nombre_mostrar") else (cliente.get("nombre","") if hasattr(cliente,"get") else str(cliente))
    story.append(Paragraph(nombre_cli, normal))
    dni = cliente.dni_cif if hasattr(cliente, "dni_cif") else (cliente.get("dni_cif", "") if hasattr(cliente, "get") else "")
    story.append(Paragraph(f"NIF/CIF: {dni}", normal))
    dir_ = cliente.direccion if hasattr(cliente, "direccion") else (cliente.get("direccion", "") if hasattr(cliente, "get") else "")
    cp = cliente.cp if hasattr(cliente, "cp") else (cliente.get("cp", "") if hasattr(cliente, "get") else "")
    ciudad = cliente.ciudad if hasattr(cliente, "ciudad") else (cliente.get("ciudad", "") if hasattr(cliente, "get") else "")
    story.append(Paragraph(f"{dir_}, {cp} {ciudad}", normal))
    story.append(Spacer(1, 6*mm))

    # Tabla de líneas
    celda = ParagraphStyle("celda", parent=normal, fontSize=10, leading=12)
    data = [["Concepto", "Cant.", "Precio", "Dto.%", "IVA %", "Total"]]
    total_descuento = 0.0
    for l in lineas:
        desc = getattr(l, "descuento", 0.0) or 0.0
        total_descuento += l.cantidad * l.importe_base * desc / 100.0
        data.append([_concepto_paragraph(l.concepto, celda), f"{l.cantidad:g}", f"{l.importe_base:.2f} €",
                    f"{desc:g}%", f"{l.porcentaje_iva:.0f}%", f"{l.total_linea:.2f} €"])
    t = Table(data, colWidths=[60*mm, 15*mm, 22*mm, 18*mm, 18*mm, 25*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ALIGN", (1,0), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Desglose IVA
    story.append(Paragraph("<b>Desglose de IVA:</b>", normal))
    for pct, (base, cuota) in desglose.items():
        story.append(Paragraph(f"IVA {pct:.0f}%: base {base:.2f} € + cuota {cuota:.2f} €", normal))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph(f"<b>Base imponible total: {factura.base_imponible:.2f} €</b>", normal))
    story.append(Paragraph(f"<b>Total descuento: {total_descuento:.2f} €</b>", normal))
    story.append(Paragraph(f"<b>Total factura: {factura.total_factura:.2f} €</b>", title))
    retencion = getattr(factura, "retencion_irpf", 0) or 0
    if retencion:
        pct = getattr(factura, "retencion_pct", 0) or 0
        story.append(Paragraph(f"Retención IRPF ({pct:g}%): −{retencion:.2f} €", normal))
        story.append(Paragraph(f"<b>Total a cobrar del cliente: {factura.total_factura - retencion:.2f} €</b>", title))

    # Registro Mercantil
    reg = getattr(empresa, "registro_mercantil", None)
    if reg:
        story.append(Spacer(1, 4*mm))
        story.append(Paragraph(f"Registro Mercantil: {reg}", normal))

    story.append(Spacer(1, 8*mm))
    if qr_path and os.path.exists(qr_path):
        story.append(Image(qr_path, width=35*mm, height=35*mm))
        if leyenda_qr:
            story.append(Paragraph("<b>VERI*FACTU</b>", normal))
            story.append(Paragraph(leyenda_qr, normal))
        else:
            story.append(Paragraph("Código de verificación (Verifactu)", normal))

def _marca_fn(texto):
    if not texto:
        return None
    def _dibuja(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica-Bold", 34)
        canvas.setFillColor(colors.Color(0.85, 0.2, 0.2, alpha=0.18))
        canvas.translate(A4[0] / 2, A4[1] / 2)
        canvas.rotate(45)
        canvas.drawCentredString(0, 0, texto)
        canvas.restoreState()
    return _dibuja

def generar_pdf_factura(factura, empresa, cliente, lineas, desglose, qr_path, destino_path,
                        leyenda_qr=None, marca=None) -> str:
    doc = SimpleDocTemplate(destino_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    title, normal = _estilos()
    story = []
    _bloque_factura(story, factura, empresa, cliente, lineas, desglose, qr_path, title, normal, leyenda_qr)
    fn = _marca_fn(marca)
    if fn:
        doc.build(story, onFirstPage=fn, onLaterPages=fn)
    else:
        doc.build(story)
    return destino_path

def generar_pdf_facturas(lista, destino_path) -> str:
    # lista: lista de dicts/tuplas con keys: factura, empresa, cliente, lineas, desglose, qr_path
    doc = SimpleDocTemplate(destino_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=15*mm, bottomMargin=15*mm)
    title, normal = _estilos()
    story = []
    for i, item in enumerate(lista):
        if i > 0:
            story.append(PageBreak())
        _bloque_factura(story, item["factura"], item["empresa"], item["cliente"],
                        item["lineas"], item["desglose"], item["qr_path"], title, normal,
                        item.get("leyenda_qr"))
    doc.build(story)
    return destino_path
