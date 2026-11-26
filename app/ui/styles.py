# app/ui/styles.py
from ..config import (FONT_SIZE_BASE, FONT_SIZE_TITLE, FONT_SIZE_BUTTON,
                      BUTTON_MIN_HEIGHT, BUTTON_MIN_WIDTH)

# Tema oscuro profesional
COLOR_GREEN = "#4caf50"   # acciones positivas
COLOR_GRAY  = "#5c5c5c"   # secundario
COLOR_RED   = "#e53935"   # peligro
COLOR_BG    = "#1e1e1e"   # fondo principal
COLOR_CARD  = "#2a2a2a"   # tarjetas/inputs
COLOR_TEXT  = "#f5f5f5"   # texto principal
COLOR_BORDER= "#3a3a3a"   # bordes
COLOR_ACCENT= "#66bb6a"

GLOBAL_QSS = f"""
QWidget {{
    font-family: "Segoe UI", "Calibri", sans-serif;
    font-size: {FONT_SIZE_BASE}px;
    background-color: {COLOR_BG};
    color: {COLOR_TEXT};
}}
QLabel {{ color: {COLOR_TEXT}; }}
QLineEdit, QTextEdit, QComboBox, QDateEdit, QSpinBox, QDoubleSpinBox {{
    min-height: 36px;
    padding: 6px 10px;
    border: 2px solid {COLOR_BORDER};
    border-radius: 6px;
    background: {COLOR_CARD};
    color: {COLOR_TEXT};
    font-size: {FONT_SIZE_BASE}px;
}}
QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{
    border-color: {COLOR_GREEN};
}}
QPushButton {{
    min-height: {BUTTON_MIN_HEIGHT}px;
    min-width: {BUTTON_MIN_WIDTH}px;
    padding: 10px 18px;
    border-radius: 8px;
    font-size: {FONT_SIZE_BUTTON}px;
    font-weight: bold;
    color: {COLOR_TEXT};
}}
QPushButton[role="primary"] {{
    background-color: {COLOR_GREEN};
    color: #0b1a0c;
    border: none;
}}
QPushButton[role="primary"]:hover {{ background-color: {COLOR_ACCENT}; }}
QPushButton[role="secondary"] {{
    background-color: {COLOR_GRAY};
    color: {COLOR_TEXT};
    border: none;
}}
QPushButton[role="secondary"]:hover {{ background-color: #6e6e6e; }}
QPushButton[role="danger"] {{
    background-color: {COLOR_RED};
    color: white;
    border: none;
}}
QPushButton[role="danger"]:hover {{ background-color: #c62828; }}
QTabWidget::pane {{ border: 2px solid {COLOR_BORDER}; border-radius: 8px; background: {COLOR_CARD}; }}
QTabBar::tab {{
    min-width: 150px;
    min-height: 60px;
    padding: 10px 16px;
    font-size: 16px;
    font-weight: bold;
    background: {COLOR_BG};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
}}
QTabBar::tab:selected {{ background: {COLOR_GREEN}; color: #0b1a0c; }}
QGroupBox {{ font-size: 16px; font-weight: bold; margin-top: 12px; color: {COLOR_TEXT}; }}
QTableWidget {{
    background: {COLOR_CARD};
    color: {COLOR_TEXT};
    gridline-color: {COLOR_BORDER};
    border: 1px solid {COLOR_BORDER};
}}
QHeaderView::section {{
    background: {COLOR_BG};
    color: {COLOR_TEXT};
    padding: 6px;
    border: 1px solid {COLOR_BORDER};
    font-weight: bold;
}}
QMessageBox {{ background: {COLOR_BG}; color: {COLOR_TEXT}; }}
QScrollArea {{ background: {COLOR_BG}; }}
QListWidget {{
    background: {COLOR_CARD};
    color: {COLOR_TEXT};
    border: 1px solid {COLOR_BORDER};
}}
"""
def primary(btn): btn.setProperty("role", "primary"); return btn
def secondary(btn): btn.setProperty("role", "secondary"); return btn
def danger(btn): btn.setProperty("role", "danger"); return btn
