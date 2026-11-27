# app/ui/tab_gastos.py
from datetime import date
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
                               QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QDateEdit,
                               QAbstractItemView)
from PySide6.QtCore import Qt, QDate
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error, confirm
from ..utils.messages import ayuda
from ..utils.validators import validar_nif_cif


class TabGastos(QWidget):
    """Facturas recibidas de proveedores: base de los gastos y del IVA soportado."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        v = QVBoxLayout(self)
        v.setSpacing(8)
        v.addWidget(title_label("Gastos (facturas recibidas)"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Fecha:"))
        self.inp_fecha = QDateEdit(QDate.currentDate())
        self.inp_fecha.setCalendarPopup(True)
        self.inp_fecha.setDisplayFormat("dd/MM/yyyy")
        row.addWidget(self.inp_fecha)
        row.addWidget(QLabel("Proveedor:"))
        self.inp_prov = QLineEdit()
        row.addWidget(self.inp_prov, 2)
        row.addWidget(QLabel("NIF/CIF:"))
        self.inp_nif = QLineEdit()
        row.addWidget(self.inp_nif, 1)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Nº factura:"))
        self.inp_num = QLineEdit()
        row.addWidget(self.inp_num, 1)
        row.addWidget(QLabel("Concepto:"))
        self.inp_conc = QLineEdit()
        row.addWidget(self.inp_conc, 2)
        v.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Base (sin IVA):"))
        self.inp_base = QLineEdit()
        self.inp_base.setPlaceholderText("0,00")
        self.inp_base.textChanged.connect(self._calc)
        row.addWidget(self.inp_base)
        row.addWidget(QLabel("IVA:"))
        self.cmb_iva = QComboBox()
        self.cmb_iva.currentIndexChanged.connect(self._calc)
        row.addWidget(self.cmb_iva)
        self.lbl_calc = QLabel("Cuota: 0,00 €   Total: 0,00 €")
        self.lbl_calc.setStyleSheet("font-weight:bold;")
        row.addWidget(self.lbl_calc)
        row.addStretch()
        v.addLayout(row)

        row = QHBoxLayout()
        self.chk_ded = QCheckBox("IVA deducible")
        self.chk_ded.setChecked(True)
        row.addWidget(self.chk_ded)
        self.chk_pag = QCheckBox("Ya pagada")
        self.chk_pag.setChecked(True)
        row.addWidget(self.chk_pag)
        row.addStretch()
        v.addLayout(row)

        row = QHBoxLayout()
        b = big_button("GUARDAR GASTO", "primary")
        b.clicked.connect(self.guardar)
        row.addWidget(b)
        b = big_button("Marcar como pagado", "secondary")
        b.setMinimumWidth(220)
        b.clicked.connect(self.marcar_pagado)
        row.addWidget(b)
        b = big_button("Quitar gasto", "danger")
        b.clicked.connect(self.quitar)
        row.addWidget(b)
        b = big_button("?", "secondary")
        b.setFixedWidth(60)
        b.clicked.connect(lambda: help_popup(self, ayuda("gastos")))
        row.addWidget(b)
        row.addStretch()
        v.addLayout(row)

        self.tabla = QTableWidget(0, 8)
        self.tabla.setHorizontalHeaderLabels(["Fecha", "Proveedor", "Nº factura", "Base", "IVA %", "Cuota", "Total", "Estado"])
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        v.addWidget(self.tabla, 1)

        self.cargar_ivas()
        self.refrescar()

    def cargar_ivas(self):
        self.cmb_iva.clear()
        conn = get_connection()
        for r in conn.execute("SELECT porcentaje FROM tipos_iva WHERE activo=1 ORDER BY orden"):
            self.cmb_iva.addItem(f"{r['porcentaje']:g}%", r["porcentaje"])
        conn.close()
        idx = self.cmb_iva.findData(21.0)
        if idx >= 0:
            self.cmb_iva.setCurrentIndex(idx)

    def _base(self):
        try:
            return float(self.inp_base.text().strip().replace(",", "."))
        except ValueError:
            return None

    def _calc(self, *_):
        base = self._base()
        pct = self.cmb_iva.currentData() or 0
        if base is None:
            self.lbl_calc.setText("Cuota: 0,00 €   Total: 0,00 €")
            return
        cuota = round(base * pct / 100.0, 2)
        self.lbl_calc.setText(f"Cuota: {cuota:.2f} €   Total: {base + cuota:.2f} €".replace(".", ","))

    def guardar(self):
        if not self.inp_prov.text().strip():
            error(self, "Falta el proveedor. Escribe aquí: ")
            self.inp_prov.setFocus()
            return
        nif = self.inp_nif.text().strip()
        if nif and not validar_nif_cif(nif):
            error(self, "El NIF/CIF del proveedor no parece correcto. Revísalo o déjalo en blanco.")
            self.inp_nif.setFocus()
            return
        base = self._base()
        if base is None or base < 0:
            error(self, "La base debe ser un número. Ejemplo: 120,50")
            self.inp_base.setFocus()
            return
        pct = float(self.cmb_iva.currentData() or 0)
        cuota = round(base * pct / 100.0, 2)
        conn = get_connection()
        conn.execute("""INSERT INTO gastos (fecha, proveedor, nif_proveedor, numero_factura, concepto,
                        base, porcentaje_iva, cuota_iva, total, iva_deducible, pagado)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                     (self.inp_fecha.date().toString("yyyy-MM-dd"), self.inp_prov.text().strip(),
                      nif.upper(), self.inp_num.text().strip(), self.inp_conc.text().strip(),
                      base, pct, cuota, round(base + cuota, 2),
                      1 if self.chk_ded.isChecked() else 0, 1 if self.chk_pag.isChecked() else 0))
        conn.commit()
        conn.close()
        for w in (self.inp_prov, self.inp_nif, self.inp_num, self.inp_conc, self.inp_base):
            w.clear()
        self.refrescar()
        self._avisar_balance()
        info(self, "Gasto guardado. Todo correcto.")

    def refrescar(self):
        self.tabla.setRowCount(0)
        conn = get_connection()
        rows = conn.execute("SELECT * FROM gastos ORDER BY fecha DESC, id DESC").fetchall()
        conn.close()
        for i, r in enumerate(rows):
            self.tabla.insertRow(i)
            try:
                f = date.fromisoformat(r["fecha"]).strftime("%d/%m/%Y")
            except ValueError:
                f = r["fecha"]
            vals = [f, r["proveedor"], r["numero_factura"] or "", f"{r['base']:.2f} €",
                    f"{r['porcentaje_iva']:g}%", f"{r['cuota_iva']:.2f} €", f"{r['total']:.2f} €",
                    ("Pagado" if r["pagado"] else "Pendiente de pago") + ("" if r["iva_deducible"] else " · IVA no deducible")]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(val)
                if c == 0:
                    it.setData(Qt.ItemDataRole.UserRole, r["id"])
                if c in (3, 4, 5, 6):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.tabla.setItem(i, c, it)

    def _sel_id(self):
        row = self.tabla.currentRow()
        if row < 0:
            error(self, "Selecciona un gasto de la lista.")
            return None
        return self.tabla.item(row, 0).data(Qt.ItemDataRole.UserRole)

    def marcar_pagado(self):
        gid = self._sel_id()
        if gid is None:
            return
        conn = get_connection()
        conn.execute("UPDATE gastos SET pagado=1 WHERE id=?", (gid,))
        conn.commit()
        conn.close()
        self.refrescar()
        self._avisar_balance()

    def quitar(self):
        gid = self._sel_id()
        if gid is None:
            return
        if not confirm(self, "¿Seguro que quieres quitar este gasto?"):
            return
        conn = get_connection()
        conn.execute("DELETE FROM gastos WHERE id=?", (gid,))
        conn.commit()
        conn.close()
        self.refrescar()
        self._avisar_balance()

    def _avisar_balance(self):
        try:
            self.parent.tab_balance.refrescar()
        except Exception:
            pass
