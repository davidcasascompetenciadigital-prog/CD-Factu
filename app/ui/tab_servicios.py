# app/ui/tab_servicios.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QTextEdit, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error, confirm
from ..utils.messages import ayuda

MSG_SERVICIO_GUARDADO = "Servicio guardado. Todo correcto."


class TabServicios(QWidget):
    """Servicios con título y descripción larga (p. ej. 'Informe pericial')."""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.editando_id = None
        v = QVBoxLayout(self)
        v.setSpacing(10)
        v.addWidget(title_label("Servicios"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Título del servicio:"))
        self.inp_titulo = QLineEdit()
        self.inp_titulo.setPlaceholderText("Ej: Informe pericial")
        row.addWidget(self.inp_titulo)
        v.addLayout(row)

        v.addWidget(QLabel("Descripción (aparecerá en la factura):"))
        self.inp_desc = QTextEdit()
        self.inp_desc.setAcceptRichText(False)
        self.inp_desc.setMinimumHeight(130)
        self.inp_desc.setPlaceholderText(
            "Ej: Informe pericial de tercero encargado por el Juzgado de Murcia, sección de "
            "Primera Instancia, sobre la valoración de una serie de daños producidos en su inmueble...")
        v.addWidget(self.inp_desc)

        row = QHBoxLayout()
        row.addWidget(QLabel("Importe base (sin IVA):"))
        self.inp_base = QLineEdit()
        self.inp_base.setPlaceholderText("0,00")
        row.addWidget(self.inp_base)
        row.addWidget(QLabel("€"))
        row.addWidget(QLabel("IVA que se aplica:"))
        self.cmb_iva = QComboBox()
        row.addWidget(self.cmb_iva)
        v.addLayout(row)

        row = QHBoxLayout()
        btn_guardar = big_button("GUARDAR SERVICIO", "primary")
        btn_guardar.clicked.connect(self.guardar)
        row.addWidget(btn_guardar)
        btn_nuevo = big_button("Nuevo", "secondary")
        btn_nuevo.clicked.connect(self.limpiar)
        row.addWidget(btn_nuevo)
        btn_borrar = big_button("Quitar", "danger")
        btn_borrar.clicked.connect(self.quitar)
        row.addWidget(btn_borrar)
        btn_help = big_button("?", "secondary")
        btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, ayuda("servicios")))
        row.addWidget(btn_help)
        row.addStretch()
        v.addLayout(row)

        v.addWidget(QLabel("Servicios guardados (pulsa uno para editarlo):"))
        self.lista = QListWidget()
        self.lista.itemClicked.connect(self.cargar_en_formulario)
        v.addWidget(self.lista, 1)

        self.cargar_ivas()
        self.refrescar_lista()

    # --- datos auxiliares
    def cargar_ivas(self):
        self.cmb_iva.clear()
        conn = get_connection()
        for r in conn.execute("SELECT id, porcentaje FROM tipos_iva WHERE activo=1 ORDER BY orden"):
            self.cmb_iva.addItem(f"{r['porcentaje']:g}%", r["id"])
        conn.close()

    def refrescar_lista(self):
        self.lista.clear()
        conn = get_connection()
        rows = conn.execute("""SELECT s.id, s.titulo, s.descripcion, s.importe_base, t.porcentaje
                               FROM servicios s LEFT JOIN tipos_iva t ON t.id=s.tipo_iva_id
                               WHERE s.activo=1 ORDER BY s.titulo""").fetchall()
        conn.close()
        for r in rows:
            pct = r["porcentaje"] if r["porcentaje"] is not None else 21
            resumen = (r["descripcion"] or "").replace("\n", " ")
            if len(resumen) > 70:
                resumen = resumen[:70] + "…"
            item = QListWidgetItem(f"{r['titulo']}  |  {r['importe_base']:.2f} €  |  IVA {pct:g}%\n    {resumen}")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            self.lista.addItem(item)

    # --- acciones
    def cargar_en_formulario(self, item):
        sid = item.data(Qt.ItemDataRole.UserRole)
        conn = get_connection()
        r = conn.execute("SELECT * FROM servicios WHERE id=?", (sid,)).fetchone()
        conn.close()
        if not r:
            return
        self.editando_id = sid
        self.inp_titulo.setText(r["titulo"] or "")
        self.inp_desc.setPlainText(r["descripcion"] or "")
        self.inp_base.setText(f"{r['importe_base']:.2f}".replace(".", ","))
        idx = self.cmb_iva.findData(r["tipo_iva_id"])
        if idx >= 0:
            self.cmb_iva.setCurrentIndex(idx)

    def limpiar(self):
        self.editando_id = None
        self.inp_titulo.clear()
        self.inp_desc.clear()
        self.inp_base.clear()
        self.lista.clearSelection()

    def guardar(self):
        titulo = self.inp_titulo.text().strip()
        if not titulo:
            error(self, "Falta el título del servicio. Escribe aquí: ")
            self.inp_titulo.setFocus()
            return
        txt = self.inp_base.text().strip().replace(",", ".") or "0"
        try:
            base = float(txt)
        except ValueError:
            error(self, "El importe base debe ser un número. Ejemplo: 150,00")
            self.inp_base.setFocus()
            return
        desc = self.inp_desc.toPlainText().strip()
        iva_id = self.cmb_iva.currentData()
        conn = get_connection()
        if self.editando_id is None:
            conn.execute("""INSERT INTO servicios (titulo, descripcion, importe_base, tipo_iva_id)
                            VALUES (?,?,?,?)""", (titulo, desc, base, iva_id))
        else:
            conn.execute("""UPDATE servicios SET titulo=?, descripcion=?, importe_base=?, tipo_iva_id=?
                            WHERE id=?""", (titulo, desc, base, iva_id, self.editando_id))
        conn.commit()
        conn.close()
        self.limpiar()
        self.refrescar_lista()
        info(self, MSG_SERVICIO_GUARDADO)

    def quitar(self):
        if self.editando_id is None:
            error(self, "Pulsa primero un servicio de la lista.")
            return
        if not confirm(self, "¿Seguro que quieres quitar este servicio? Las facturas ya emitidas no cambian."):
            return
        conn = get_connection()
        conn.execute("UPDATE servicios SET activo=0 WHERE id=?", (self.editando_id,))
        conn.commit()
        conn.close()
        self.limpiar()
        self.refrescar_lista()
