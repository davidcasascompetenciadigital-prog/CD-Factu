# app/ui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QStackedWidget, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QGridLayout, QMessageBox)
from PySide6.QtCore import Qt, Slot
from pathlib import Path
from PySide6.QtGui import QPixmap, QIcon

from ..config import resource_path, BACKUP_DIR
from ..db.database import get_connection
from ..ui.styles import GLOBAL_QSS
from ..ui.widgets import title_label, big_button, help_popup, info
from ..utils.messages import ayuda
from ..services.sample_data import seed_sample_data
from ..version import VERSION, RELEASES_URL, API_URL
from ..updater import descargar_y_actualizar
from ..services.backup import backup_semanal, listar_backups, restaurar_backup

from .tab_empresa import TabEmpresa
from .tab_clientes import TabClientes
from .tab_productos import TabProductos
from .tab_emitir import TabEmitir
from .tab_cobros import TabCobros
from .tab_facturas import TabFacturas

PAGES = [
    ("Mis datos de empresa", "tab_empresa"),
    ("Clientes", "tab_clientes"),
    ("Productos", "tab_productos"),
    ("Emitir factura", "tab_emitir"),
    ("Cobros", "tab_cobros"),
    ("Facturas emitidas", "tab_facturas"),
]

class MenuCard(QWidget):
    """Ficha única: icono + nombre de la función + concepto en un solo recuadro."""
    clicked = None
    def __init__(self, icono, titulo, descripcion, callback):
        super().__init__()
        self.callback = callback
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QWidget#card { background:#2a2a2a; border:2px solid #3a3a3a; border-radius:12px; }"
                          "QWidget#card:hover { border:2px solid #4caf50; }")
        self.setObjectName("card")
        h = QHBoxLayout(self)
        h.setSpacing(14)
        h.setContentsMargins(16, 12, 16, 12)
        lbl_icon = QLabel(icono)
        lbl_icon.setStyleSheet("font-size:44px;")
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setFixedWidth(60)
        h.addWidget(lbl_icon)
        v = QVBoxLayout()
        v.setSpacing(2)
        lbl_tit = QLabel(titulo)
        lbl_tit.setStyleSheet("font-size:18px; font-weight:bold; color:#f5f5f5;")
        v.addWidget(lbl_tit)
        lbl_desc = QLabel(descripcion)
        lbl_desc.setStyleSheet("font-size:13px; color:#aaaaaa;")
        lbl_desc.setWordWrap(True)
        v.addWidget(lbl_desc)
        h.addLayout(v, 1)
        self.setMinimumHeight(90)
        self.setMinimumWidth(320)

    def mousePressEvent(self, event):
        if self.callback:
            self.callback()
        super().mousePressEvent(event)

MENU_ITEMS = [
    ("🏢", "Mis datos de empresa", "Configura los datos de tu empresa, IVA y Verifactu.", "tab_empresa"),
    ("👥", "Clientes", "Gestiona tus clientes y sus contactos.", "tab_clientes"),
    ("📦", "Productos", "Crea y edita tus productos y precios.", "tab_productos"),
    ("🧾", "Emitir factura", "Crea una nueva factura y genera el PDF.", "tab_emitir"),
    ("💰", "Cobros", "Registra los pagos de tus facturas.", "tab_cobros"),
    ("📄", "Facturas emitidas", "Consulta, imprime y gestiona facturas.", "tab_facturas"),
]

class MainMenu(QWidget):
    def __init__(self, navigate):
        super().__init__()
        v = QVBoxLayout(self)
        v.setSpacing(20)
        v.addStretch()
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
            grid.addWidget(card, i // 2, i % 2)
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
            pix = QPixmap(str(resource_path("assets/factufacil_logo.png"))).scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_logo.setPixmap(pix)
            header.addWidget(lbl_logo)
        except Exception:
            pass
        header.addWidget(title_label("CD Factu"))
        header.addStretch()
        btn_menu = big_button("Menú principal", "secondary")
        btn_menu.setFixedWidth(170)
        btn_menu.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        header.addWidget(btn_menu)
        self.btn_sample = big_button("Datos de ejemplo", "secondary")
        self.btn_sample.setFixedWidth(160)
        self.btn_sample.clicked.connect(self.cargar_ejemplos)
        header.addWidget(self.btn_sample)

        btn_backup = big_button("Backup", "secondary")
        btn_backup.setFixedWidth(120)
        btn_backup.clicked.connect(self.hacer_backup)
        header.addWidget(btn_backup)

        btn_restore = big_button("Restaurar", "secondary")
        btn_restore.setFixedWidth(120)
        btn_restore.clicked.connect(self.restaurar_backup_ui)
        header.addWidget(btn_restore)
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

        self.pages = {
            "tab_empresa": self.tab_empresa,
            "tab_clientes": self.tab_clientes,
            "tab_productos": self.tab_productos,
            "tab_emitir": self.tab_emitir,
            "tab_cobros": self.tab_cobros,
            "tab_facturas": self.tab_facturas,
        }
        for key in ["tab_empresa","tab_clientes","tab_productos","tab_emitir","tab_cobros","tab_facturas"]:
            self.stack.addWidget(self.pages[key])

        layout.addWidget(self.stack, 1)

        # Pie con datos del programa/empresa/versión
        self.footer = QHBoxLayout()
        self.lbl_prog = QLabel("Programa: CD Factu")
        self.lbl_emp = QLabel("Empresa: -")
        self.lbl_ver = QLabel(f"Versión: {VERSION}")
        for l in (self.lbl_prog, self.lbl_emp, self.lbl_ver):
            l.setStyleSheet("color:#aaaaaa; font-size:12px;")
            self.footer.addWidget(l)
        self.footer.addStretch()
        layout.addLayout(self.footer)

        self.actualizar_footer()
        self.actualizar_boton_ejemplos()
        self.stack.setCurrentIndex(0)
        self.verificar_actualizacion()
        # Primera ejecución: preguntar si se desean datos de ejemplo
        try:
            conn = get_connection()
            empty = (conn.execute("SELECT COUNT(*) AS c FROM clientes").fetchone()["c"] == 0 and
                     conn.execute("SELECT COUNT(*) AS c FROM facturas").fetchone()["c"] == 0)
            conn.close()
            if empty:
                from PySide6.QtWidgets import QMessageBox
                r = QMessageBox.question(self, "CD Factu",
                                         "¿Desea cargar datos de ejemplo para probar el programa?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if r == QMessageBox.StandardButton.Yes:
                    self.cargar_ejemplos()
                self.actualizar_boton_ejemplos()
        except Exception:
            pass

    def ir_a(self, key):
        idx = list(self.pages.keys()).index(key) + 1
        self.stack.setCurrentIndex(idx)
        try:
            self.statusBar().showMessage(ayuda(key.replace("tab_","")), 8000)
        except Exception:
            pass

    def verificar_actualizacion(self):
        import threading, json, urllib.request
        def worker():
            try:
                req = urllib.request.Request(API_URL, headers={"User-Agent": "CD-Factu"})
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                tag = (data.get("tag_name") or "").strip().lstrip("v")
                if not tag:
                    return
                def parse(v):
                    parts = []
                    for p in v.split("."):
                        num = ""
                        for ch in p:
                            if ch.isdigit():
                                num += ch
                            else:
                                break
                        parts.append(int(num) if num else 0)
                    return tuple(parts)
                if parse(tag) > parse(VERSION):
                    self._release_data = data
                    from PySide6.QtCore import QMetaObject, Qt as _Qt
                    QMetaObject.invokeMethod(self, "_mostrar_aviso_actualizacion",
                                            _Qt.ConnectionType.QueuedConnection,
                                            __import__("PySide6.QtCore", fromlist=["Q_ARG"]).Q_ARG(str, tag))
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    @Slot(str)
    def _mostrar_aviso_actualizacion(self, nueva):
        from PySide6.QtWidgets import QMessageBox
        r = QMessageBox.question(self, "Nueva versión disponible",
                                 f"Hay una nueva versión disponible: v{nueva}\n"
                                 f"Tu versión actual es v{VERSION}.\n\n"
                                 "¿Deseas descargarla e instalarla ahora?\n"
                                 "(Se respetarán tus datos existentes.)",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            data = getattr(self, "_release_data", None)
            if data:
                descargar_y_actualizar(self, data)
            else:
                from PySide6.QtGui import QDesktopServices
                from PySide6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl(RELEASES_URL))

    @Slot(str)
    def _error_actualizacion(self, msg):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Actualización", f"No se pudo actualizar: {msg}")

    def closeEvent(self, event):
        # Backup automático al cerrar el programa (preserva los datos del usuario)
        try:
            backup_semanal()
        except Exception:
            pass
        super().closeEvent(event)

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
            info(self, msg)
            self.actualizar_boton_ejemplos()
        except Exception as e:
            error(self, f"No se pudieron cargar los datos de ejemplo: {e}")

    def actualizar_boton_ejemplos(self):
        try:
            conn = get_connection()
            n_cli = conn.execute("SELECT COUNT(*) AS c FROM clientes").fetchone()["c"]
            n_fac = conn.execute("SELECT COUNT(*) AS c FROM facturas").fetchone()["c"]
            conn.close()
            if n_cli > 0 or n_fac > 0:
                self.btn_sample.hide()
            else:
                self.btn_sample.show()
        except Exception:
            pass

    def hacer_backup(self):
        from ..ui.widgets import info, error
        try:
            p = backup_semanal()
            info(self, f"Copia de seguridad creada:\n{p}")
        except Exception as e:
            error(self, f"No se pudo crear la copia de seguridad: {e}")

    def restaurar_backup_ui(self):
        from ..ui.widgets import confirm, info, error
        from PySide6.QtWidgets import QFileDialog
        backups = listar_backups()
        if backups:
            carpeta = str(BACKUP_DIR)
        else:
            carpeta = str(Path.home())
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar copia de seguridad", carpeta,
                                            "Base de datos (*.db);;Todos los archivos (*)")
        if not path:
            return
        if not confirm(self, "¿Restaurar la copia de seguridad seleccionada?\n"
                            "Se creará una copia de la BD actual antes de restaurar.\n"
                            "Será necesario reiniciar el programa."):
            return
        if restaurar_backup(Path(path)):
            info(self, "Copia restaurada correctamente. Reinicie el programa para aplicar los cambios.")
        else:
            error(self, "No se pudo restaurar la copia de seguridad.")

    def mostrar_acerca_de(self):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PySide6.QtCore import Qt, Slot
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
        ver = QLabel("Versión 0.0.1 (inicial)")
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