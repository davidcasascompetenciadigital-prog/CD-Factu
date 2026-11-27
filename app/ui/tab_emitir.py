# app/ui/tab_emitir.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QDialog, QListWidget, QListWidgetItem, QTextEdit,
                                QFrame, QSizePolicy)
from PySide6.QtCore import Qt
from datetime import date
import os
from ..db.database import get_connection
from ..models.factura import Factura, LineaFactura
from ..services.hash_chain import hash_registro_factura, qr_payload_url
from ..services.qr_generator import generar_qr_png
from ..services.pdf_generator import generar_pdf_factura
from ..ui.widgets import big_button, title_label, help_popup, info, error, confirm
from ..utils.messages import MSG_FACTURA_GUARDADA, ayuda
from ..config import FACTURAS_DIR

class SelectorClienteDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Elegir cliente")
        self.setMinimumSize(560, 440)
        v = QVBoxLayout(self)
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("Buscar por CIF, nombre, dirección, email o teléfono (mín. 4 caracteres)...")
        self.inp.textChanged.connect(self.filtrar)
        v.addWidget(self.inp)
        self.lbl_hint = QLabel("Escribe al menos 4 caracteres para ver sugerencias.")
        v.addWidget(self.lbl_hint)
        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(lambda it: self.accept())
        v.addWidget(self.lista)
        btn = big_button("Elegir", "primary")
        btn.clicked.connect(self.accept)
        v.addWidget(btn)
        self.clientes = []
        self.cargar()
    def cargar(self):
        conn = get_connection()
        rows = conn.execute("""SELECT id, nombre, apellidos, empresa, dni_cif, direccion, cp, ciudad,
                               comunidad_autonoma, pais FROM clientes""").fetchall()
        contacts = conn.execute("SELECT cliente_id, telefono, email FROM contactos_cliente").fetchall()
        conn.close()
        contact_map = {}
        for c in contacts:
            contact_map.setdefault(c["cliente_id"], []).append((c["telefono"] or "", c["email"] or ""))
        self.clientes = []
        for r in rows:
            cid = r["id"]
            ct = contact_map.get(cid, [])
            telefonos = " ".join(t for t, e in ct)
            emails = " ".join(e for t, e in ct)
            self.clientes.append({
                "id": cid,
                "nombre": r["nombre"] or "",
                "apellidos": r["apellidos"] or "",
                "empresa": r["empresa"] or "",
                "dni_cif": r["dni_cif"] or "",
                "direccion": r["direccion"] or "",
                "cp": r["cp"] or "",
                "ciudad": r["ciudad"] or "",
                "comunidad": r["comunidad_autonoma"] or "",
                "pais": r["pais"] or "",
                "telefonos": telefonos,
                "emails": emails,
            })
        self.filtrar(self.inp.text())
    def _texto_cliente(self, c):
        partes = [c["nombre"], c["apellidos"], c["empresa"], c["dni_cif"], c["direccion"],
                   c["cp"], c["ciudad"], c["comunidad"], c["pais"], c["telefonos"], c["emails"]]
        return " ".join(p for p in partes if p).lower()
    def filtrar(self, texto):
        self.lista.clear()
        t = (texto or "").strip().lower()
        if not t:
            self.lbl_hint.setText("Listado de clientes. Doble clic para seleccionar.")
        else:
            self.lbl_hint.setText(f"Sugerencias para: {texto.strip()}")
        for c in self.clientes:
            if (not t) or (t in self._texto_cliente(c)):
                nombre = (c["nombre"] + " " + c["apellidos"]).strip()
                if c["empresa"]:
                    nombre += f"  |  Empresa: {c['empresa']}"
                if c["dni_cif"]:
                    nombre += f"  |  CIF: {c['dni_cif']}"
                if c["telefonos"]:
                    nombre += f"  |  Tel: {c['telefonos']}"
                if c["emails"]:
                    nombre += f"  |  Email: {c['emails']}"
                item = QListWidgetItem(nombre)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                self.lista.addItem(item)
    def seleccionado_id(self):
        it = self.lista.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

class SelectorProductoDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Elegir producto")
        self.setMinimumSize(500, 400)
        v = QVBoxLayout(self)
        self.lista = QListWidget()
        self.lista.itemDoubleClicked.connect(lambda it: self.accept())
        v.addWidget(self.lista)
        btn = big_button("Añadir", "primary")
        btn.clicked.connect(self.accept)
        v.addWidget(btn)
        conn = get_connection()
        rows = conn.execute("""SELECT p.id, p.nombre, p.importe_base, t.porcentaje, t.id AS iva_id
                               FROM productos p LEFT JOIN tipos_iva t ON t.id=p.tipo_iva_id
                               WHERE p.activo=1 ORDER BY p.nombre""").fetchall()
        conn.close()
        for r in rows:
            item = QListWidgetItem(f"{r['nombre']}  |  {r['importe_base']:.2f} €  |  IVA {r['porcentaje']:g}%")
            item.setData(Qt.ItemDataRole.UserRole, dict(r))
            self.lista.addItem(item)
    def seleccionado(self):
        it = self.lista.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

class SelectorServicioDialog(QDialog):
    """Elige un servicio y permite ajustar su descripcion antes de anadirlo a la factura."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Elegir servicio")
        self.setMinimumSize(640, 520)
        v = QVBoxLayout(self)
        self.lista = QListWidget()
        self.lista.setMaximumHeight(170)
        v.addWidget(self.lista)
        v.addWidget(QLabel("Descripción en la factura (puedes editarla solo para esta factura):"))
        self.txt = QTextEdit()
        self.txt.setAcceptRichText(False)
        v.addWidget(self.txt, 1)
        row = QHBoxLayout()
        row.addWidget(QLabel("Importe base (sin IVA):"))
        self.inp_base = QLineEdit()
        row.addWidget(self.inp_base)
        row.addWidget(QLabel("€"))
        v.addLayout(row)
        btn = big_button("Añadir a la factura", "primary")
        btn.clicked.connect(self._aceptar)
        v.addWidget(btn)
        conn = get_connection()
        rows = conn.execute("""SELECT s.id, s.titulo, s.descripcion, s.importe_base, t.porcentaje, t.id AS iva_id
                               FROM servicios s LEFT JOIN tipos_iva t ON t.id=s.tipo_iva_id
                               WHERE s.activo=1 ORDER BY s.titulo""").fetchall()
        conn.close()
        for r in rows:
            d = dict(r)
            if d["porcentaje"] is None:
                d["porcentaje"] = 21.0
            item = QListWidgetItem(f"{d['titulo']}  |  {d['importe_base']:.2f} €  |  IVA {d['porcentaje']:g}%")
            item.setData(Qt.ItemDataRole.UserRole, d)
            self.lista.addItem(item)
        self.lista.currentItemChanged.connect(self._cambio)
        self._sel = None

    def _cambio(self, cur, prev):
        if not cur:
            return
        d = cur.data(Qt.ItemDataRole.UserRole)
        self._sel = d
        self.txt.setPlainText(d["descripcion"] or "")
        self.inp_base.setText(f"{d['importe_base']:.2f}".replace(".", ","))

    def _aceptar(self):
        if not self._sel:
            error(self, "Elige un servicio de la lista.")
            return
        try:
            float(self.inp_base.text().replace(",", "."))
        except ValueError:
            error(self, "El importe base debe ser un número.")
            return
        self.accept()

    def resultado(self):
        d = dict(self._sel)
        d["descripcion"] = self.txt.toPlainText().strip()
        d["importe_base"] = float(self.inp_base.text().replace(",", "."))
        return d

class TabEmitir(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.cliente_id = None
        self.cliente_data = None
        self.lineas = []
        outer = QHBoxLayout(self)
        outer.setSpacing(16)

        # ===== Columna izquierda: formulario =====
        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(title_label("Emitir factura"))

        # 1. Cliente: búsqueda inline + botón de listado (autor)
        left.addWidget(QLabel("1. Cliente:"))
        self.lbl_cliente = QLabel("Ningún cliente seleccionado")
        self.lbl_cliente.setStyleSheet(
            "font-size:16px; padding:8px; background:#2a2a2a; border:1px solid #3a3a3a; border-radius:6px;")
        left.addWidget(self.lbl_cliente)
        self.inp_buscar_cliente = QLineEdit()
        self.inp_buscar_cliente.setPlaceholderText("Buscar cliente (nombre, CIF, email, teléfono)...")
        self.inp_buscar_cliente.textChanged.connect(self.filtrar_clientes)
        left.addWidget(self.inp_buscar_cliente)
        self.lista_clientes = QListWidget()
        self.lista_clientes.setMaximumHeight(150)
        self.lista_clientes.itemClicked.connect(self.seleccionar_cliente_lista)
        left.addWidget(self.lista_clientes)
        self._clientes = []
        self.cargar_clientes()
        row = QHBoxLayout()
        btn_listado = big_button("Listado de clientes", "secondary")
        btn_listado.clicked.connect(self.abrir_listado_clientes)
        row.addWidget(btn_listado)
        btn_sel = big_button("Elegir cliente", "primary")
        btn_sel.clicked.connect(self.elegir_cliente)
        row.addWidget(btn_sel)
        row.addStretch()
        left.addLayout(row)

        # 2. Líneas
        left.addWidget(QLabel("2. Líneas de factura:"))
        row = QHBoxLayout()
        btn_prod = big_button("Añadir producto", "primary")
        btn_prod.clicked.connect(self.add_producto)
        row.addWidget(btn_prod)
        btn_serv = big_button("Añadir servicio", "primary")
        btn_serv.clicked.connect(self.add_servicio)
        row.addWidget(btn_serv)
        btn_manual = big_button("Escribir línea a mano", "secondary")
        btn_manual.clicked.connect(self.add_manual)
        row.addWidget(btn_manual)
        row.addStretch()
        left.addLayout(row)

        self.tabla = QTableWidget(0, 7)
        self.tabla.setHorizontalHeaderLabels(["Concepto", "Cantidad", "Precio", "Dto.%", "IVA", "Total", "Quitar"])
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setMinimumHeight(180)
        self.tabla.verticalHeader().setDefaultSectionSize(32)
        self.tabla.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        left.addWidget(self.tabla)
        left.addStretch()

        # ===== Columna derecha: resumen y opciones =====
        right = QVBoxLayout()
        right.setSpacing(10)
        right.addWidget(QLabel("3. Resumen automático:"))
        box = QFrame()
        box.setStyleSheet("background:#1e1e1e; border:1px solid #3a3a3a; border-radius:10px;")
        bv = QVBoxLayout(box)
        bv.setContentsMargins(14, 14, 14, 14)
        self.lbl_base = QLabel("Base imponible total: 0,00 €")
        self.lbl_iva = QLabel("IVA total: 0,00 €")
        self.lbl_desglose = QLabel("")
        self.lbl_total = QLabel("Total factura: 0,00 €")
        self.lbl_total.setStyleSheet("font-size:20px; font-weight:bold; color:#4caf50;")
        self.lbl_retencion = QLabel("Retención: 0,00 € · A cobrar del cliente: 0,00 €")
        self.lbl_retencion.setStyleSheet("color:#aaaaaa; font-size:13px;")
        for l in (self.lbl_base, self.lbl_iva, self.lbl_desglose, self.lbl_total, self.lbl_retencion):
            l.setAlignment(Qt.AlignmentFlag.AlignRight)
            bv.addWidget(l)
        bv.addStretch()
        right.addWidget(box)

        # Retención IRPF (la practica el cliente)
        right.addWidget(QLabel("Retención IRPF (la practica el cliente sobre la base imponible):"))
        row = QHBoxLayout()
        self.cmb_retencion = QComboBox()
        for pct in (0, 7, 15, 19, 20, 21):
            self.cmb_retencion.addItem(f"{pct}%", pct)
        row.addWidget(self.cmb_retencion)
        row.addStretch()
        right.addLayout(row)
        self.cmb_retencion.currentIndexChanged.connect(self.recalcular_resumen)

        # Datos del cliente seleccionado
        right.addWidget(QLabel("Datos del cliente:"))
        box_cli = QFrame()
        box_cli.setStyleSheet("background:#1e1e1e; border:1px solid #3a3a3a; border-radius:10px;")
        bcv = QVBoxLayout(box_cli)
        bcv.setContentsMargins(14, 14, 14, 14)
        self.lbl_cli_datos = QLabel("Ningún cliente seleccionado")
        self.lbl_cli_datos.setWordWrap(True)
        self.lbl_cli_datos.setStyleSheet("font-size:13px; color:#dddddd;")
        bcv.addWidget(self.lbl_cli_datos)
        bcv.addStretch()
        right.addWidget(box_cli)

        # 4. Estado de cobro
        right.addWidget(QLabel("4. Estado de cobro inicial:"))
        row = QHBoxLayout()
        self.cmb_cobro = QComboBox()
        self.cmb_cobro.addItems(["No cobrada", "Cobrada totalmente", "Cobrada parcialmente"])
        row.addWidget(self.cmb_cobro)
        row.addStretch()
        right.addLayout(row)

        # Campos de pago visibles si está cobrada
        self.pago_frame = QWidget()
        pf = QVBoxLayout(self.pago_frame)
        r = QHBoxLayout()
        r.addWidget(QLabel("Importe a cobrar:"))
        self.inp_importe_cobro = QLineEdit()
        r.addWidget(self.inp_importe_cobro)
        pf.addLayout(r)
        r = QHBoxLayout()
        r.addWidget(QLabel("Forma de pago:"))
        self.cmb_forma = QComboBox()
        self.cmb_forma.addItems(["Efectivo", "Transferencia", "Tarjeta", "Bizum", "Cheque", "Otro"])
        r.addWidget(self.cmb_forma)
        pf.addLayout(r)
        r = QHBoxLayout()
        r.addWidget(QLabel("Fecha:"))
        self.inp_fecha_cobro = QLineEdit(date.today().isoformat())
        r.addWidget(self.inp_fecha_cobro)
        pf.addLayout(r)
        self.pago_frame.setVisible(False)
        self.cmb_cobro.currentTextChanged.connect(lambda t: self.pago_frame.setVisible(t != "No cobrada"))
        right.addWidget(self.pago_frame)

        # 5. Verifactu
        right.addWidget(QLabel("5. Verifactu (Agencia Tributaria):"))
        row = QHBoxLayout()
        self.cmb_vf = QComboBox()
        self.cmb_vf.addItem("No enviar ahora", "no")
        self.cmb_vf.addItem("Ver vista previa Verifactu (no se envía)", "previa")
        self.cmb_vf.addItem("Enviar al entorno de PRUEBAS de la AEAT", "pruebas")
        self.cmb_vf.addItem("Enviar a la AEAT (REAL)", "real")
        self.cmb_vf.setMinimumWidth(340)
        row.addWidget(self.cmb_vf)
        self.lbl_vf = QLabel("")
        self.lbl_vf.setWordWrap(True)
        self.lbl_vf.setStyleSheet("color:#aaaaaa; font-size:13px;")
        row.addWidget(self.lbl_vf)
        right.addLayout(row)
        self.cmb_vf.currentIndexChanged.connect(self._aviso_vf)
        self._vf_por_defecto()

        # Botones
        row = QHBoxLayout()
        btn_emitir = big_button("EMITIR FACTURA Y GENERAR PDF", "primary")
        btn_emitir.clicked.connect(self.emitir)
        row.addWidget(btn_emitir)
        btn_help = big_button("?", "secondary")
        btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, ayuda("emitir")))
        row.addWidget(btn_help)
        row.addStretch()
        right.addLayout(row)
        right.addStretch()

        outer.addLayout(left, 2)
        outer.addLayout(right, 1)

    def _vf_por_defecto(self):
        """Preselecciona según la configuración de empresa (nunca envía sin confirmación)."""
        try:
            conn = get_connection()
            r = conn.execute("SELECT verifactu_enabled, verifactu_mode FROM empresa WHERE id=1").fetchone()
            conn.close()
            if r and r["verifactu_enabled"]:
                data = "real" if r["verifactu_mode"] == "real" else "pruebas"
                self.cmb_vf.setCurrentIndex(self.cmb_vf.findData(data))
        except Exception:
            pass
        self._aviso_vf()

    def _aviso_vf(self, *_):
        d = self.cmb_vf.currentData()
        self.lbl_vf.setText({"no": "Podrás hacerlo después desde «Facturas emitidas».",
                             "previa": "Se abrirá una vista previa con el QR; no se guarda ni se envía.",
                             "pruebas": "Sin efectos fiscales. Pide confirmación.",
                             "real": "Registro REAL en la AEAT. Pide doble confirmación."}.get(d, ""))

    def cargar_clientes(self):
        conn = get_connection()
        rows = conn.execute("""SELECT id, nombre, apellidos, empresa, dni_cif, direccion, cp, ciudad
                               FROM clientes ORDER BY nombre""").fetchall()
        contacts = conn.execute("SELECT cliente_id, telefono, email FROM contactos_cliente").fetchall()
        conn.close()
        contact_map = {}
        for c in contacts:
            contact_map.setdefault(c["cliente_id"], []).append((c["telefono"] or "", c["email"] or ""))
        self._clientes = []
        for r in rows:
            ct = contact_map.get(r["id"], [])
            telefonos = " ".join(t for t, e in ct)
            emails = " ".join(e for t, e in ct)
            self._clientes.append({
                "id": r["id"],
                "nombre": r["nombre"] or "",
                "apellidos": r["apellidos"] or "",
                "empresa": r["empresa"] or "",
                "dni_cif": r["dni_cif"] or "",
                "direccion": r["direccion"] or "",
                "cp": r["cp"] or "",
                "ciudad": r["ciudad"] or "",
                "telefonos": telefonos,
                "emails": emails,
            })
        self.filtrar_clientes(self.inp_buscar_cliente.text())

    def _texto_cliente(self, c):
        return " ".join([c["nombre"], c["apellidos"], c["empresa"], c["dni_cif"],
                         c["direccion"], c["cp"], c["ciudad"], c["telefonos"], c["emails"]]).lower()

    def filtrar_clientes(self, texto):
        self.lista_clientes.clear()
        t = (texto or "").strip().lower()
        for c in self._clientes:
            if t and t not in self._texto_cliente(c):
                continue
            nombre = (c["nombre"] + " " + c["apellidos"]).strip()
            if c["empresa"]:
                nombre += f"  |  Empresa: {c['empresa']}"
            if c["dni_cif"]:
                nombre += f"  |  CIF: {c['dni_cif']}"
            item = QListWidgetItem(nombre)
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.lista_clientes.addItem(item)

    def seleccionar_cliente_lista(self, item):
        cid = item.data(Qt.ItemDataRole.UserRole)
        if cid is not None:
            self._set_cliente(cid)

    def elegir_cliente(self):
        # compatibilidad: abre el primer resultado filtrado
        if self.lista_clientes.count() > 0:
            self.seleccionar_cliente_lista(self.lista_clientes.item(0))

    def abrir_listado_clientes(self):
        dlg = SelectorClienteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cid = dlg.seleccionado_id()
            if cid is not None:
                self._set_cliente(cid)

    def _set_cliente(self, cid):
        self.cliente_id = cid
        conn = get_connection()
        r = conn.execute("""SELECT id, nombre, apellidos, empresa, dni_cif, direccion, cp, ciudad,
                            comunidad_autonoma, pais FROM clientes WHERE id=?""", (cid,)).fetchone()
        contacts = conn.execute("SELECT telefono, email FROM contactos_cliente WHERE cliente_id=?", (cid,)).fetchall()
        conn.close()
        if not r:
            return
        self.cliente_data = dict(r)
        tels = ", ".join(c["telefono"] for c in contacts if c["telefono"])
        emails = ", ".join(c["email"] for c in contacts if c["email"])
        self.cliente_data["telefonos"] = tels
        self.cliente_data["emails"] = emails
        nombre = f"{r['nombre']} {r['apellidos'] or ''}".strip()
        self.lbl_cliente.setText(nombre + (f"  |  Empresa: {r['empresa']}" if r["empresa"] else ""))
        datos = (f"Nombre: {nombre}\n"
                 f"Empresa: {r['empresa'] or '-'}\n"
                 f"NIF/CIF: {r['dni_cif'] or '-'}\n"
                 f"Dirección: {r['direccion'] or '-'}\n"
                 f"CP/Ciudad: {r['cp'] or ''} {r['ciudad'] or ''}\n"
                 f"Teléfono: {tels or '-'}\n"
                 f"Email: {emails or '-'}")
        self.lbl_cli_datos.setText(datos)

    def add_producto(self):
        dlg = SelectorProductoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.seleccionado()
            if not data: return
            linea = LineaFactura(concepto=data["nombre"] if "nombre" in data else data.get("nombre",""),
                                cantidad=1.0, importe_base=float(data["importe_base"]),
                                porcentaje_iva=float(data["porcentaje"]), producto_id=data["id"],
                                tipo_iva_id=data["iva_id"])
            # fetch nombre properly
            conn = get_connection()
            r = conn.execute("SELECT nombre FROM productos WHERE id=?", (data["id"],)).fetchone()
            conn.close()
            linea.concepto = r["nombre"]
            linea.recalcular()
            self.lineas.append(linea)
            self.refrescar_tabla()
            self.recalcular_resumen()

    def add_servicio(self):
        dlg = SelectorServicioDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        d = dlg.resultado()
        concepto = d["titulo"] + (("\n" + d["descripcion"]) if d["descripcion"] else "")
        linea = LineaFactura(concepto=concepto, cantidad=1.0, importe_base=d["importe_base"],
                             porcentaje_iva=float(d["porcentaje"]), tipo_iva_id=d["iva_id"])
        linea.recalcular()
        self.lineas.append(linea)
        self.refrescar_tabla()
        self.recalcular_resumen()

    def add_manual(self):
        # mini dialog inline: ask concepto, base, iva
        from PySide6.QtWidgets import QInputDialog
        concepto, ok = QInputDialog.getText(self, "Línea manual", "Concepto:")
        if not ok or not concepto.strip(): return
        base_str, ok = QInputDialog.getText(self, "Línea manual", "Importe base (sin IVA):")
        if not ok: return
        try:
            base = float(base_str.replace(",", "."))
        except ValueError:
            error(self, "El importe base debe ser un número.")
            return
        # IVA selector
        dlg = QDialog(self)
        dlg.setWindowTitle("IVA")
        v = QVBoxLayout(dlg)
        cmb = QComboBox()
        conn = get_connection()
        for r in conn.execute("SELECT id, porcentaje FROM tipos_iva WHERE activo=1 ORDER BY orden"):
            cmb.addItem(f"{r['porcentaje']:g}%", r["id"])
        conn.close()
        v.addWidget(QLabel("IVA que se aplica:"))
        v.addWidget(cmb)
        btn = big_button("Aceptar", "primary")
        btn.clicked.connect(dlg.accept)
        v.addWidget(btn)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        iva_id = cmb.currentData()
        conn = get_connection()
        r = conn.execute("SELECT porcentaje FROM tipos_iva WHERE id=?", (iva_id,)).fetchone()
        conn.close()
        pct = r["porcentaje"] if r else 21.0
        linea = LineaFactura(concepto=concepto.strip(), cantidad=1.0, importe_base=base,
                            porcentaje_iva=pct, tipo_iva_id=iva_id)
        linea.recalcular()
        self.lineas.append(linea)
        self.refrescar_tabla()
        self.recalcular_resumen()

    def refrescar_tabla(self):
        self.tabla.setRowCount(0)
        for i, l in enumerate(self.lineas):
            self.tabla.insertRow(i)
            self.tabla.setItem(i, 0, QTableWidgetItem(l.concepto))
            # Cantidad (editable)
            from PySide6.QtWidgets import QLineEdit
            inp_cant = QLineEdit(f"{l.cantidad:g}")
            inp_cant.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inp_cant.textChanged.connect(lambda t, idx=i: self._cambiar_cantidad(idx, t))
            self.tabla.setCellWidget(i, 1, inp_cant)
            it_precio = QTableWidgetItem(f"{l.importe_base:.2f} €")
            it_precio.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(i, 2, it_precio)
            # Descuento % (editable)
            inp_desc = QLineEdit(f"{l.descuento:g}")
            inp_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
            inp_desc.textChanged.connect(lambda t, idx=i: self._cambiar_descuento(idx, t))
            self.tabla.setCellWidget(i, 3, inp_desc)
            it_iva = QTableWidgetItem(f"{l.porcentaje_iva:g}%")
            it_iva.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabla.setItem(i, 4, it_iva)
            it_total = QTableWidgetItem(f"{l.total_linea:.2f} €")
            it_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabla.setItem(i, 5, it_total)
            btn = big_button("Quitar", "danger")
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, idx=i: self.quitar_linea(idx))
            self.tabla.setCellWidget(i, 6, btn)
        self.tabla.setMinimumHeight(max(180, self.tabla.rowCount() * 34 + 40))

    def _cambiar_cantidad(self, idx, texto):
        if idx < 0 or idx >= len(self.lineas):
            return
        try:
            c = float((texto or "1").replace(",", "."))
            if c <= 0:
                c = 1.0
        except ValueError:
            c = 1.0
        self.lineas[idx].cantidad = c
        self.lineas[idx].recalcular()
        self.refrescar_tabla()
        self.recalcular_resumen()

    def _cambiar_descuento(self, idx, texto):
        if idx < 0 or idx >= len(self.lineas):
            return
        try:
            d = float((texto or "0").replace(",", "."))
        except ValueError:
            d = 0.0
        self.lineas[idx].descuento = d
        self.lineas[idx].recalcular()
        self.refrescar_tabla()
        self.recalcular_resumen()

    def quitar_linea(self, idx):
        if not confirm(self, "¿Seguro que quieres quitar esta línea?"):
            return
        if 0 <= idx < len(self.lineas):
            self.lineas.pop(idx)
            self.refrescar_tabla()
            self.recalcular_resumen()

    def recalcular_resumen(self, *_):
        f = Factura(lineas=self.lineas)
        f.recalcular_totales()
        pct = self.cmb_retencion.currentData() or 0
        f.aplicar_retencion(pct)
        self.lbl_base.setText(f"Base imponible total: {f.base_imponible:.2f} €")
        self.lbl_iva.setText(f"IVA total: {f.total_iva:.2f} €")
        desglose_txt = "  |  ".join(f"IVA {pct:g}%: {cuota:.2f} €" for pct, (b, cuota) in f.desglose_iva.items())
        self.lbl_desglose.setText(desglose_txt)
        self.lbl_total.setText(f"Total factura: {f.total_factura:.2f} €")
        self.lbl_retencion.setText(
            f"Retención {pct:g}% ({f.retencion_irpf:.2f} €) · A cobrar del cliente: {f.pendiente:.2f} €"
        )
        self._totales_cache = f

    def emitir(self):
        if self.cliente_id is None:
            error(self, "Falta elegir un cliente. Pulsa 'Elegir cliente'.")
            return
        if not self.lineas:
            error(self, "Añade al menos una línea de factura.")
            return
        f = Factura(lineas=[LineaFactura(**{k: getattr(l, k) for k in l.__dataclass_fields__}) for l in self.lineas])
        # rebuild cleanly
        f.lineas = []
        for l in self.lineas:
            nl = LineaFactura(concepto=l.concepto, cantidad=l.cantidad, importe_base=l.importe_base,
                              porcentaje_iva=l.porcentaje_iva, descuento=l.descuento,
                              producto_id=l.producto_id, tipo_iva_id=l.tipo_iva_id)
            nl.recalcular()
            f.lineas.append(nl)
        f.recalcular_totales()
        f.aplicar_retencion(self.cmb_retencion.currentData() or 0)
        # cliente nombre para confirmación
        nombre_cliente = self.cliente_data.get("empresa") or f"{self.cliente_data['nombre']} {self.cliente_data.get('apellidos') or ''}".strip()
        if not confirm(self, f"Vas a emitir una factura a {nombre_cliente} por {f.total_factura:.2f} € "
                             f"(a cobrar tras la retención: {f.pendiente:.2f} €). ¿Es correcto?"):
            return
        # número de factura
        conn = get_connection()
        año = date.today().year
        cur = conn.execute("SELECT COUNT(*) AS c FROM facturas WHERE strftime('%Y', fecha_emision)=?", (str(año),))
        seq = (cur.fetchone()["c"] or 0) + 1
        numero = f"{año}-{seq:06d}"
        # hash anterior
        last = conn.execute("SELECT hash_registro FROM registros_facturacion ORDER BY id DESC LIMIT 1").fetchone()
        hash_anterior = last["hash_registro"] if last else None
        nif_receptor = self.cliente_data.get("dni_cif") or ""
        # nif emisor
        emp = conn.execute("SELECT nif, verifactu_enabled FROM empresa WHERE id=1").fetchone()
        nif_emisor = (emp["nif"] if emp else "") or ""
        verificable = bool(emp["verifactu_enabled"]) if emp and "verifactu_enabled" in emp.keys() else False
        hash_reg = hash_registro_factura(numero, date.today().isoformat(), nif_emisor, nif_receptor,
                                        f.base_imponible, f.total_factura, hash_anterior)
        qr_payload = qr_payload_url(numero, nif_emisor, date.today().isoformat(), f.total_factura, verificable)

        # insert factura
        cur = conn.execute("""INSERT INTO facturas (numero, fecha_emision, cliente_id, base_imponible, total_iva,
                              total_factura, retencion_irpf, estado, estado_cobro, pendiente, hash_registro, hash_anterior)
                              VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                           (numero, date.today().isoformat(), self.cliente_id, f.base_imponible,
                            f.total_iva, f.total_factura, f.retencion_irpf, "emitida", "no_cobrada", f.pendiente,
                            hash_reg, hash_anterior))
        factura_id = cur.lastrowid
        # lineas
        for i, l in enumerate(f.lineas):
            conn.execute("""INSERT INTO lineas_factura (factura_id, orden, producto_id, concepto, cantidad,
                            importe_base, tipo_iva_id, porcentaje_iva, base_linea, iva_linea, total_linea)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                         (factura_id, i, l.producto_id, l.concepto, l.cantidad, l.importe_base,
                          l.tipo_iva_id, l.porcentaje_iva, l.base_linea, l.iva_linea, l.total_linea))
        # desglose
        for pct, (base, cuota) in f.desglose_iva.items():
            # tipo_iva_id lookup
            t = conn.execute("SELECT id FROM tipos_iva WHERE porcentaje=?", (pct,)).fetchone()
            tid = t["id"] if t else None
            conn.execute("""INSERT INTO desglose_iva_factura (factura_id, tipo_iva_id, porcentaje, base, cuota)
                            VALUES (?,?,?,?,?)""", (factura_id, tid, pct, base, cuota))
        # registro facturacion
        conn.execute("""INSERT INTO registros_facturacion (factura_id, tipo, numero_factura, fecha_emision,
                        nif_emisor, nif_receptor, base_imponible, total_factura, hash_registro,
                        hash_anterior, qr_payload)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                     (factura_id, "alta", numero, date.today().isoformat(), nif_emisor, nif_receptor,
                      f.base_imponible, f.total_factura, hash_reg, hash_anterior, qr_payload))
        conn.commit()

        # QR
        qr_path = FACTURAS_DIR / str(año) / f"{numero}.png"
        qr_path.parent.mkdir(parents=True, exist_ok=True)
        generar_qr_png(qr_payload, qr_path)

        # PDF
        pdf_path = FACTURAS_DIR / str(año) / f"{numero}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        # build cliente-like object
        class C: pass
        c = C()
        c.nombre = self.cliente_data["nombre"]; c.apellidos = self.cliente_data.get("apellidos")
        c.empresa = self.cliente_data.get("empresa"); c.dni_cif = self.cliente_data.get("dni_cif")
        c.direccion = self.cliente_data.get("direccion"); c.cp = self.cliente_data.get("cp")
        c.ciudad = self.cliente_data.get("ciudad")
        def _nombre_mostrar():
            if c.empresa: return f"Empresa: {c.empresa}"
            return f"{c.nombre} {c.apellidos or ''}".strip()
        c.nombre_mostrar = _nombre_mostrar
        # empresa
        er = conn.execute("SELECT * FROM empresa WHERE id=1").fetchone()
        class E: pass
        e = E()
        e.nombre = er["nombre"]; e.nif = er["nif"]; e.direccion = er["direccion"]
        e.cp = er["cp"]; e.ciudad = er["ciudad"]; e.comunidad_autonoma = er["comunidad_autonoma"]
        e.pais = er["pais"]; e.logo_path = er["logo_path"]
        e.registro_mercantil = er["registro_mercantil"] if "registro_mercantil" in er.keys() else None
        f.numero = numero
        f.fecha_emision = date.today().isoformat()
        generar_pdf_factura(f, e, c, f.lineas, f.desglose_iva, str(qr_path), str(pdf_path))
        conn.execute("UPDATE facturas SET pdf_path=? WHERE id=?", (str(pdf_path), factura_id))
        # estado cobro inicial
        estado = self.cmb_cobro.currentText()
        if estado == "Cobrada totalmente":
            imp = f.pendiente  # el cliente paga la factura menos la retención que le practica
            conn.execute("""INSERT INTO cobros (factura_id, fecha_cobro, importe, forma_pago) VALUES (?,?,?,?)""",
                         (factura_id, date.today().isoformat(), imp, self.cmb_forma.currentText()))
            conn.execute("UPDATE facturas SET estado_cobro='pagada', pendiente=0 WHERE id=?", (factura_id,))
        elif estado == "Cobrada parcialmente":
            try:
                imp = float(self.inp_importe_cobro.text().replace(",", "."))
            except ValueError:
                imp = f.total_factura
            conn.execute("""INSERT INTO cobros (factura_id, fecha_cobro, importe, forma_pago) VALUES (?,?,?,?)""",
                         (factura_id, self.inp_fecha_cobro.text() or date.today().isoformat(),
                          imp, self.cmb_forma.currentText()))
            pend = round(f.pendiente - imp, 2)
            nuevo_estado = "pagada" if pend <= 0 else "parcial"
            conn.execute("UPDATE facturas SET estado_cobro=?, pendiente=? WHERE id=?",
                         (nuevo_estado, max(pend, 0), factura_id))
        conn.commit()
        conn.close()

        # abrir PDF
        try:
            os.startfile(str(pdf_path))
        except Exception:
            pass

        info(self, MSG_FACTURA_GUARDADA)
        opcion_vf = self.cmb_vf.currentData()
        # reset
        self.lineas = []
        self.cliente_id = None
        self.cliente_data = None
        self.lbl_cliente.setText("Ningún cliente seleccionado")
        self.lbl_cli_datos.setText("Ningún cliente seleccionado")
        self.refrescar_tabla()
        self.cmb_retencion.setCurrentIndex(0)
        self.recalcular_resumen()
        self.cmb_cobro.setCurrentText("No cobrada")
        self.pago_frame.setVisible(False)
        # refrescar otras pestañas
        try:
            self.parent.tab_facturas.refrescar()
            self.parent.tab_cobros.refrescar()
            self.parent.tab_balance.refrescar()
            self.parent.tab_balance_anual.refrescar()
        except Exception:
            pass
        # Verifactu segun lo elegido (la factura ya esta emitida y guardada)
        if opcion_vf != "no":
            try:
                from .dialog_verifactu import VerifactuDialog
                dlg = VerifactuDialog(self.parent, factura_id)
                if opcion_vf == "previa":
                    dlg.vista_previa()
                else:
                    dlg.enviar(opcion_vf)
                dlg.exec()
            except Exception as e:
                error(self, f"La factura se emitió correctamente, pero Verifactu falló: {e}")
