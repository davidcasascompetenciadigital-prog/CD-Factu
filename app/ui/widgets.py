# app/ui/widgets.py
from PySide6.QtWidgets import QPushButton, QLabel, QLineEdit, QComboBox, QMessageBox
from ..ui.styles import primary, secondary, danger
from ..config import FONT_SIZE_TITLE

def big_button(text, role="primary"):
    b = QPushButton(text)
    if role == "primary": primary(b)
    elif role == "secondary": secondary(b)
    elif role == "danger": danger(b)
    b.setCursor(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.CursorShape.PointingHandCursor)
    return b

def title_label(text):
    l = QLabel(text)
    l.setStyleSheet(f"font-size: {FONT_SIZE_TITLE}px; font-weight: bold; color: #212121;")
    return l

def help_popup(parent, texto):
    QMessageBox.information(parent, "Ayuda", texto)

def confirm(parent, texto):
    r = QMessageBox.question(parent, "Confirmar", texto,
                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return r == QMessageBox.StandardButton.Yes

def info(parent, texto):
    QMessageBox.information(parent, "Todo correcto", texto)

def error(parent, texto):
    QMessageBox.warning(parent, "Revisa esto", texto)
