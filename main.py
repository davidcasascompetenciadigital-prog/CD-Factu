# main.py
import sys, ctypes, subprocess, os
from ctypes import wintypes

def _msg(titulo, texto, flags=0x40):
    try:
        ctypes.windll.user32.MessageBoxW(None, texto, titulo, flags)
    except Exception:
        pass

def ensure_runtime():
    # Verificar runtime de Visual C++ (necesario en Windows antiguos)
    try:
        ctypes.CDLL("vcruntime140.dll")
    except OSError:
        # Intento de instalación automática (best-effort)
        _msg("CD Factu", "Falta el runtime de Visual C++. Se intentará instalar automáticamente.", 0x40)
        try:
            subprocess.run(["winget", "install", "--id", "Microsoft.VCRedist.2015+.x64",
                            "-e", "--silent", "--accept-source-agreements",
                            "--accept-package-agreements"], check=False)
        except Exception:
            pass
        try:
            ctypes.CDLL("vcruntime140.dll")
        except OSError:
            _msg("CD Factu", "No se pudo instalar el runtime automáticamente.\n"
                             "Descárguelo desde Microsoft y vuelva a ejecutar el programa.", 0x10)
            sys.exit(1)
    # Verificar versión mínima de Windows
    try:
        ver = sys.getwindowsversion()
        if ver.major < 10:
            _msg("CD Factu", "Este programa está optimizado para Windows 10 o superior.\n"
                             "En versiones anteriores puede no funcionar correctamente.", 0x30)
    except Exception:
        pass

ensure_runtime()

from PySide6.QtWidgets import QApplication, QSplashScreen
from PySide6.QtGui import QPixmap, QColor
from PySide6.QtCore import Qt

from app.config import resource_path
from app.db.database import init_db
from app.ui.main_window import MainWindow
from app.ui.styles import GLOBAL_QSS

def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(GLOBAL_QSS)

    # Pantalla de bienvenida: grande, sin quedarse encima de otras ventanas
    splash_pix = QPixmap(str(resource_path("assets/factufacil_logo.png")))
    if not splash_pix.isNull():
        splash_pix = splash_pix.scaled(480, 480, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
    splash = QSplashScreen(splash_pix)
    splash.showMessage("CD Factu - Cargando...", Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter,
                       QColor("#f5f5f5"))
    splash.show()
    app.processEvents()

    init_db()

    w = MainWindow()
    w.showMaximized()
    splash.finish(w)   # se cierra en cuanto la ventana principal es visible
    w.primera_ejecucion()   # preguntas de primera ejecucion, ya sin el logo delante
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

