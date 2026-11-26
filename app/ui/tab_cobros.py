# app/ui/tab_cobros.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QDateEdit)
from PySide6.QtCore import QDate, Qt
from datetime import date
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error, confirm
from ..utils.messages import ayuda

class TabCobros(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.addWidget(title_label("Cobros"))

        v.addWidget(QLabel("Facturas no cobradas o parcialmente cobradas:"))
        self.tabla = QTableWidget(0, 5)
        self.tabla.setHorizontalHeaderLabels(["Cliente", "Nº Factura", "Total", "Pendiente", ""])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(260)
        v.addWidget(self.tabla)

        # Mini-formulario de cobro
        v.addWidget(QLabel("Registrar cobro:"))
        self.frm = QWidget()
        f = QHBoxLayout(self.frm)
        f.addWidget(QLabel("Factura seleccionada:")); self.lbl_sel = QLabel("-"); f.addWidget(self.lbl_sel)
        f.addWidget(QLabel("Importe a cobrar:")); self.inp_importe = QLineEdit(); f.addWidget(self.inp_importe)
        f.addWidget(QLabel("Forma de pago:")); self.cmb_forma = QComboBox()
        self.cmb_forma.addItems(["Efectivo","Transferencia","Tarjeta","Bizum","Cheque","Otro"]); f.addWidget(self.cmb_forma)
        f.addWidget(QLabel("Fecha:")); self.inp_fecha = QLineEdit(date.today().isoformat()); f.addWidget(self.inp_fecha)
        v.addWidget(self.frm)

        row = QHBoxLayout()
        btn = big_button("CONFIRMAR COBRO", "primary")
        btn.clicked.connect(self.confirmar)
        row.addWidget(btn)
        btn_help = big_button("?", "secondary"); btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, ayuda("cobros")))
        row.addWidget(btn_help)
        row.addStretch()
        v.addLayout(row)
        v.addStretch()

        self.factura_sel = None
        self.refrescar()

    def refrescar(self):
        self.tabla.setRowCount(0)
        conn = get_connection()
        rows = conn.execute("""
            SELECT f.id, f.numero, f.total_factura, f.pendiente, c.nombre, c.apellidos, c.empresa
            FROM facturas f JOIN clientes c ON c.id=f.cliente_id
            WHERE f.estado='emitida' AND f.estado_cobro IN ('no_cobrada','parcial')
            ORDER BY f.fecha_emision
        """).fetchall()
        conn.close()
        for i, r in enumerate(rows):
            self.tabla.insertRow(i)
            nombre = r["empresa"] if r["empresa"] else f"{r['nombre']} {r['apellidos'] or ''}".strip()
            self.tabla.setItem(i, 0, QTableWidgetItem(nombre))
            self.tabla.setItem(i, 1, QTableWidgetItem(r["numero"]))
            self.tabla.setItem(i, 2, QTableWidgetItem(f"{r['total_factura']:.2f} €"))
            self.tabla.setItem(i, 3, QTableWidgetItem(f"{r['pendiente']:.2f} €"))
            btn = big_button("Registrar cobro", "primary")
            btn.setMinimumWidth(140)
            btn.clicked.connect(lambda checked, fid=r["id"], pend=r["pendiente"]: self.seleccionar(fid, pend))
            self.tabla.setCellWidget(i, 4, btn)

    def seleccionar(self, fid, pend):
        self.factura_sel = fid
        self.lbl_sel.setText(str(fid))
        self.inp_importe.setText(f"{pend:.2f}")

    def confirmar(self):
        if self.factura_sel is None:
            error(self, "Pulsa 'Registrar cobro' en una factura de la lista.")
            return
        try:
            imp = float(self.inp_importe.text().replace(",", "."))
        except ValueError:
            error(self, "El importe debe ser un número.")
            return
        if imp <= 0:
            error(self, "El importe debe ser mayor que cero.")
            return
        conn = get_connection()
        r = conn.execute("SELECT pendiente, total_factura FROM facturas WHERE id=?", (self.factura_sel,)).fetchone()
        pendiente = r["pendiente"]
        if imp > pendiente + 0.001:
            error(self, "El importe no puede ser mayor que el pendiente.")
            conn.close()
            return
        conn.execute("""INSERT INTO cobros (factura_id, fecha_cobro, importe, forma_pago) VALUES (?,?,?,?)""",
                     (self.factura_sel, self.inp_fecha.text() or date.today().isoformat(),
                      imp, self.cmb_forma.currentText()))
        nuevo_pend = round(pendiente - imp, 2)
        nuevo_estado = "pagada" if nuevo_pend <= 0.001 else "parcial"
        conn.execute("UPDATE facturas SET estado_cobro=?, pendiente=? WHERE id=?",
                     (nuevo_estado, max(nuevo_pend, 0), self.factura_sel))
        conn.commit()
        conn.close()
        info(self, "Cobro registrado. Todo correcto.")
        self.factura_sel = None
        self.lbl_sel.setText("-")
        self.refrescar()
        try:
            self.parent.tab_facturas.refrescar()
        except Exception:
            pass
