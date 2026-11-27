# app/ui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

from ..config import resource_path
from ..db.database import get_connection
from ..ui.styles import GLOBAL_QSS
from ..ui.widgets import title_label, big_button, help_popup, info
from ..utils.messages import ayuda
from ..services.sample_data import seed_sample_data

from .tab_empresa import TabEmpresa
from .tab_clientes import TabClientes
from .tab_productos import TabProductos
from .tab_emitir import TabEmitir
from .tab_cobros import TabCobros
from .tab_facturas import TabFacturas
from .tab_servicios import TabServicios
from .tab_gastos import TabGastos
from .tab_balance import TabBalance

PAGES = [
    ("Mis datos de empresa", "tab_empresa"),
    ("Clientes", "tab_clientes"),
    ("Productos", "tab_productos"),
    ("Emitir factura", "tab_emitir"),
    ("Cobros", "tab_cobros"),
    ("Facturas emitidas", "tab_facturas"),
]

class MenuCard(QWidget):
    clicked = None
    def __init__(self, icono, titulo, descripcion, callback):
        super().__init__()
        self.callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QFrame { background:#2a2a2a; border:2px solid #3a3a3a; border-radius:12px; }")
        v = QVBoxLayout(self)
        v.setSpacing(6)
        v.setContentsMargins(16, 16, 16, 16)
        lbl_icon = QLabel(icono)
        lbl_icon.setStyleSheet("font-size:40px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_icon)
        lbl_tit = QLabel(titulo)
        lbl_tit.setStyleSheet("font-size:18px; font-weight:bold; color:#f5f5f5;")
        lbl_tit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_tit)
        lbl_desc = QLabel(descripcion)
        lbl_desc.setStyleSheet("font-size:13px; color:#aaaaaa;")
        lbl_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_desc.setWordWrap(True)
        v.addWidget(lbl_desc)
        self.setMinimumHeight(140)
        self.setMinimumWidth(260)

    def mousePressEvent(self, event):
        if self.callback:
            self.callback()
        super().mousePressEvent(event)

MENU_ITEMS = [
    ("🏢", "Mis datos de empresa", "Configura los datos de tu empresa, IVA y Verifactu.", "tab_empresa"),
    ("👥", "Clientes", "Gestiona tus clientes y sus contactos.", "tab_clientes"),
    ("📦", "Productos", "Crea y edita tus productos y precios.", "tab_productos"),
    ("🛠️", "Servicios", "Servicios con título y descripción larga para tus facturas.", "tab_servicios"),
    ("🧾", "Emitir factura", "Crea una nueva factura y genera el PDF.", "tab_emitir"),
    ("💰", "Cobros", "Registra los pagos de tus facturas.", "tab_cobros"),
    ("📄", "Facturas emitidas", "Consulta, imprime y gestiona facturas.", "tab_facturas"),
    ("🧮", "Gastos", "Apunta las facturas que recibes de proveedores.", "tab_gastos"),
    ("📊", "Balance trimestral", "Ingresos, gastos, cobros e IVA del trimestre (modelo 303).", "tab_balance"),
]

class MainMenu(QWidget):
    def __init__(self, navigate):
        super().__init__()
        v = QVBoxLayout(self)
        v.setSpacing(20)
        v.addStretch()
        lbl_logo = QLabel()
        pix = QPixmap(str(resource_path("assets/factufacil_logo.png")))
        if not pix.isNull():
            lbl_logo.setPixmap(pix.scaled(220, 220, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation))
        lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lbl_logo)
        title = title_label("CD Factu")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)
        sub = QLabel("Menú principal")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("font-size:18px; color:#aaaaaa;")
        v.addWidget(sub)
        grid = QGridLayout()
        grid.setSpacing(16)
        for i, (icono, titulo, desc, key) in enumerate(MENU_ITEMS):
            card = MenuCard(icono, titulo, desc, lambda k=key: navigate(k))
            grid.addWidget(card, i // 3, i % 3)
        v.addLayout(grid)
        v.addStretch()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CD Factu")
        self.setMinimumSize(1100, 720)
        self.setStyleSheet(GLOBAL_QSS)
        try:
            self.setWindowIcon(QIcon(str(resource_path("assets/factufacil_logo.png"))))
        except Exception:
            pass

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)

        # Cabecera
        header = QHBoxLayout()
        try:
            lbl_logo = QLabel()
            pix = QPixmap(str(resource_path("assets/factufacil_logo.png"))).scaled(56, 56, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            header.addWidget(lbl_logo)
        except Exception:
            pass
        header.addWidget(title_label("CD Factu"))
        header.addStretch()
        btn_menu = big_button("Menú principal", "secondary")
        btn_menu.setFixedWidth(150)
        btn_menu.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_menu)
        btn_sample = big_button("Datos de ejemplo", "secondary")
        btn_sample.setFixedWidth(160)
        btn_sample.clicked.connect(self.cargar_ejemplos)
        header.addWidget(btn_sample)
        btn_about = big_button("Acerca de", "secondary")
        btn_about.setFixedWidth(120)
        btn_about.clicked.connect(self.mostrar_acerca_de)
        header.addWidget(btn_about)
        btn_help = big_button("?", "secondary")
        btn_help.setFixedWidth(60)
        btn_help.clicked.connect(lambda: help_popup(self, "Pulsa un botón del menú principal para empezar. "
                                                         "El botón ? en cada pantalla explica qué hacer."))
        header.addWidget(btn_help)
        layout.addLayout(header)

        # Páginas
        self.stack = QStackedWidget()
        self.main_menu = MainMenu(self.ir_a)
        self.stack.addWidget(self.main_menu)  # index 0

        self.tab_empresa = TabEmpresa(self)
        self.tab_clientes = TabClientes(self)
        self.tab_productos = TabProductos(self)
        self.tab_emitir = TabEmitir(self)
        self.tab_cobros = TabCobros(self)
        self.tab_facturas = TabFacturas(self)
        self.tab_servicios = TabServicios(self)
        self.tab_gastos = TabGastos(self)
        self.tab_balance = TabBalance(self)

        self.pages = {
            "tab_empresa": self.tab_empresa,
            "tab_clientes": self.tab_clientes,
            "tab_productos": self.tab_productos,
            "tab_emitir": self.tab_emitir,
            "tab_cobros": self.tab_cobros,
            "tab_facturas": self.tab_facturas,
            "tab_servicios": self.tab_servicios,
            "tab_gastos": self.tab_gastos,
            "tab_balance": self.tab_balance,
        }
        for key in self.pages:
            self.stack.addWidget(self.pages[key])

        layout.addWidget(self.stack, 1)

        # Pie con datos del programa/empresa/versión
        self.footer = QHBoxLayout()
        self.lbl_prog = QLabel("Programa: CD Factu")
        self.lbl_emp = QLabel("Empresa: -")
        self.lbl_ver = QLabel("Versión: 0.0.2")
        for l in (self.lbl_prog, self.lbl_emp, self.lbl_ver):
            l.setStyleSheet("color:#aaaaaa; font-size:12px;")
            self.footer.addWidget(l)
        self.footer.addStretch()
        layout.addLayout(self.footer)

        self.actualizar_footer()
        self.stack.setCurrentIndex(0)

    def primera_ejecucion(self):
        """Pregunta por datos de ejemplo (se llama con la ventana ya visible y sin el logo de carga)."""
        try:
            conn = get_connection()
            empty = (conn.execute("SELECT COUNT(*) AS c FROM clientes").fetchone()["c"] == 0 and
                     conn.execute("SELECT COUNT(*) AS c FROM facturas").fetchone()["c"] == 0)
            conn.close()
            if empty:
                r = QMessageBox.question(self, "CD Factu",
                                         "¿Desea cargar datos de ejemplo para probar el programa?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if r == QMessageBox.StandardButton.Yes:
                    self.cargar_ejemplos()
        except Exception:
            pass

    def ir_a(self, key):
        idx = list(self.pages.keys()).index(key) + 1
        self.stack.setCurrentIndex(idx)
        try:
            if key == "tab_balance":
                self.tab_balance.refrescar()
            elif key == "tab_gastos":
                self.tab_gastos.cargar_ivas()
            elif key == "tab_servicios":
                self.tab_servicios.cargar_ivas()
        except Exception:
            pass
        try:
            self.statusBar().showMessage(ayuda(key.replace("tab_","")), 8000)
        except Exception:
            pass

    def actualizar_footer(self):
        try:
            conn = get_connection()
            r = conn.execute("SELECT nombre, nif FROM empresa WHERE id=1").fetchone()
            conn.close()
            nombre = r["nombre"] if r and r["nombre"] else "-"
            self.lbl_emp.setText(f"Empresa: {nombre}")
        except Exception:
            self.lbl_emp.setText("Empresa: -")

    def cargar_ejemplos(self):
        from ..ui.widgets import confirm, info, error
        if not confirm(self, "Se cargarán datos de ejemplo (empresa, clientes, productos y facturas). ¿Continuar?"):
            return
        try:
            msg = seed_sample_data()
            self.actualizar_footer()
            try: self.tab_clientes.refrescar_lista()
            except Exception: pass
            try: self.tab_productos.refrescar_lista()
            except Exception: pass
            try: self.tab_facturas.refrescar()
            except Exception: pass
            try: self.tab_cobros.refrescar()
            except Exception: pass
            try: self.tab_empresa.cargar()
            except Exception: pass
            try: self.tab_balance.refrescar()
            except Exception: pass
            info(self, msg)
        except Exception as e:
            error(self, f"No se pudieron cargar los datos de ejemplo: {e}")

    def mostrar_acerca_de(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt
        dlg = QDialog(self)
        dlg.setWindowTitle("Acerca de CD Factu")
        dlg.setMinimumWidth(420)
        v = QVBoxLayout(dlg)
        v.setSpacing(10)
        try:
            lbl_logo = QLabel()
            pix = QPixmap(str(resource_path("assets/factufacil_logo.png"))).scaled(96, 96, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            lbl_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(lbl_logo)
        except Exception:
            pass
        title = QLabel("CD Factu")
        title.setStyleSheet("font-size:24px; font-weight:bold; color:#4caf50;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(title)
        ver = QLabel("Versión 0.0.2")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color:#aaaaaa; font-size:12px;")
        v.addWidget(ver)
        sub = QLabel("Programa de facturación local para España")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(sub)
        v.addWidget(QLabel("Creador: David Casas M."))
        v.addWidget(QLabel("Licencia: Creative Commons Compartir Igual Mención (CC BY-SA)"))
        v.addWidget(QLabel("Software GRATUITO."))
        nw = QLabel("AVISO: Este software se proporciona \"tal cual\", SIN GARANTÍA de ningún tipo, "
                    "ni expresa ni implícita. El usuario asume toda la responsabilidad de su uso.")
        nw.setWordWrap(True)
        nw.setStyleSheet("color:#e53935; font-weight:bold;")
        v.addWidget(nw)
        v.addWidget(QLabel("Redes sociales:"))
        links = [
            ("YouTube", "https://www.youtube.com/@Competencia_Digital"),
            ("Twitch", "https://www.twitch.tv/davidcasasm"),
            ("GitHub", "https://github.com/davidcasascompetenciadigital-prog"),
        ]
        for nombre, url in links:
            lbl = QLabel(f'<a href="{url}" style="color:#4caf50;">{nombre}: {url}</a>')
            lbl.setOpenExternalLinks(True)
            v.addWidget(lbl)
        btn = QPushButton("Cerrar")
        btn.clicked.connect(dlg.accept)
        from ..ui.styles import secondary
        secondary(btn)
        v.addWidget(btn)
        dlg.exec()