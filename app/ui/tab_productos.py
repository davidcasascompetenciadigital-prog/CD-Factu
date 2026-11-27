# app/ui/tab_productos.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QComboBox, QPushButton, QListWidget, QListWidgetItem)
from ..db.database import get_connection
from ..ui.widgets import big_button, title_label, help_popup, info, error
from ..utils.messages import MSG_PRODUCTO_GUARDADO, ayuda

class TabProductos(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.editando_id = None
        self._productos = []
        outer = QHBoxLayout(self)
        outer.setSpacing(16)

        # ===== Columna izquierda: formulario de nuevo producto =====
        left = QVBoxLayout()
        left.setSpacing(10)
        left.addWidget(title_label("Productos"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Referencia:")); self.inp_ref = QLineEdit(); row.addWidget(self.inp_ref)
        left.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Código de barras/QR:")); self.inp_cod = QLineEdit(); row.addWidget(self.inp_cod)
        left.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Nombre del producto:")); self.inp_nombre = QLineEdit(); row.addWidget(self.inp_nombre)
        left.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("Importe base (sin IVA):")); self.inp_base = QLineEdit(); row.addWidget(self.inp_base)
        row.addWidget(QLabel("€"))
        left.addLayout(row)

        row = QHBoxLayout()
        row.addWidget(QLabel("IVA que se aplica:")); self.cmb_iva = QComboBox(); row.addWidget(self.cmb_iva)
        left.addLayout(row)

        row = QHBoxLayout()
        btn_guardar = big_button("GUARDAR PRODUCTO", "primary")
        btn_guardar.clicked.connect(self.guardar)
        row.addWidget(btn_guardar)
        btn_help = big_button("?", "secondary"); btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, ayuda("productos") +
              " Si no sabes qué IVA aplicar, elige 21%."))
        row.addWidget(btn_help)
        row.addStretch()
        left.addLayout(row)
        left.addStretch()

        # ===== Columna derecha: búsqueda + listado =====
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(QLabel("Buscar producto:"))
        self.inp_buscar = QLineEdit()
        self.inp_buscar.setPlaceholderText("Escribe para filtrar por nombre o referencia...")
        self.inp_buscar.textChanged.connect(self.refrescar_lista)
        right.addWidget(self.inp_buscar)

        right.addWidget(QLabel("Productos guardados:"))
        self.lista = QListWidget()
        right.addWidget(self.lista, 1)

        outer.addLayout(left, 1)
        outer.addLayout(right, 1)

        self.cargar_ivas()
        self.refrescar_lista()

    def cargar_ivas(self):
        self.cmb_iva.clear()
        conn = get_connection()
        for r in conn.execute("SELECT id, porcentaje FROM tipos_iva WHERE activo=1 ORDER BY orden"):
            self.cmb_iva.addItem(f"{r['porcentaje']:g}%", r["id"])
        conn.close()

    def guardar(self):
        if not self.inp_nombre.text().strip():
            error(self, "Falta el nombre del producto. Escribe aquí: ")
            self.inp_nombre.setFocus()
            return
        try:
            base = float(self.inp_base.text().replace(",", "."))
        except ValueError:
            error(self, "El importe base debe ser un número. Ejemplo: 10,50")
            self.inp_base.setFocus()
            return
        iva_id = self.cmb_iva.currentData()
        conn = get_connection()
        if self.editando_id is None:
            conn.execute("""INSERT INTO productos (referencia, codigo_barras, nombre, importe_base, tipo_iva_id) VALUES (?,?,?,?,?)""",
                         (self.inp_ref.text().strip(), self.inp_cod.text().strip(),
                          self.inp_nombre.text().strip(), base, iva_id))
        else:
            conn.execute("""UPDATE productos SET referencia=?, codigo_barras=?, nombre=?, importe_base=?, tipo_iva_id=? WHERE id=?""",
                         (self.inp_ref.text().strip(), self.inp_cod.text().strip(),
                          self.inp_nombre.text().strip(), base, iva_id, self.editando_id))
        conn.commit()
        conn.close()
        self.limpiar()
        self.refrescar_lista()
        info(self, MSG_PRODUCTO_GUARDADO)

    def limpiar(self):
        for w in (self.inp_ref, self.inp_cod, self.inp_nombre, self.inp_base):
            w.clear()

    def refrescar_lista(self):
        self.lista.clear()
        filtro = self.inp_buscar.text().strip().lower() if hasattr(self, "inp_buscar") else ""
        conn = get_connection()
        rows = conn.execute("""SELECT p.id, p.referencia, p.nombre, p.importe_base, t.porcentaje
                               FROM productos p LEFT JOIN tipos_iva t ON t.id=p.tipo_iva_id
                               ORDER BY p.nombre""").fetchall()
        conn.close()
        for r in rows:
            texto = f"{r['nombre']}  |  {r['importe_base']:.2f} €  |  IVA {r['porcentaje']:g}%"
            if filtro:
                if filtro not in (r["nombre"] or "").lower() and filtro not in (r["referencia"] or "").lower():
                    continue
            self.lista.addItem(texto)
