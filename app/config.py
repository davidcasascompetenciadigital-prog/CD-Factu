# app/config.py
import os
from pathlib import Path

APP_NAME = "CD Factu"

# Carpeta de datos del usuario según plataforma
if os.name == "nt":
    _data_base = Path(os.environ.get("APPDATA", Path.home()))
else:
    _data_base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

DATA_DIR = _data_base / APP_NAME
DB_PATH = DATA_DIR / "facturas.db"

# Carpeta de copias de seguridad: Escritorio si existe, si no el home
_desktop = Path.home() / "Desktop"
BACKUP_DIR = (_desktop if _desktop.exists() else Path.home()) / "Backup_Facturas"
FACTURAS_DIR = DATA_DIR / "Facturas"
LOGO_DIR = DATA_DIR / "logos"

for d in (DATA_DIR, BACKUP_DIR, FACTURAS_DIR, LOGO_DIR):
    d.mkdir(parents=True, exist_ok=True)

import sys
from pathlib import Path as _Path
def resource_path(rel: str) -> _Path:
    base = _Path(getattr(sys, "_MEIPASS", _Path(__file__).resolve().parents[1]))
    # parents[1] = project root (app/ -> parent is project root)
    return base / rel

# Tamaños de fuente para usabilidad extrema
FONT_SIZE_BASE = 16
FONT_SIZE_TITLE = 22
FONT_SIZE_BUTTON = 18
BUTTON_MIN_HEIGHT = 52
BUTTON_MIN_WIDTH = 180

# Colores
COLOR_GREEN = "#2e7d32"   # acciones positivas
COLOR_GRAY  = "#757575"   # cancelar
COLOR_RED   = "#c62828"   # avisos
COLOR_BG    = "#f5f5f5"
COLOR_CARD  = "#ffffff"
