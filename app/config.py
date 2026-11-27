# app/config.py
import os
from pathlib import Path

# Carpeta de datos del usuario (Windows: %APPDATA%\ClamGuardFacturas)
APP_NAME = "CD Factu"
DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
DB_PATH = DATA_DIR / "facturas.db"
BACKUP_DIR = Path.home() / "Desktop" / "Backup_Facturas"
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


# --- Datos del sistema informatico de facturacion (SIF) -> bloque <SistemaInformatico> del registro Verifactu
APP_VERSION = "0.0.6"
SISTEMA_NOMBRE = "CD Factu"
SISTEMA_ID = "CD"                     # identificador del SIF (2 caracteres)
PRODUCTOR_NOMBRE = "David Casas M."   # razon social del productor del software
PRODUCTOR_NIF = ""                    # <-- NIF del productor del software (obligatorio para enviar a la AEAT)
