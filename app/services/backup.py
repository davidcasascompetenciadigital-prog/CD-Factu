# app/services/backup.py
import shutil, datetime
from pathlib import Path
from ..config import DB_PATH, BACKUP_DIR

def backup_semanal() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    destino = BACKUP_DIR / f"backup_{stamp}.db"
    shutil.copy2(DB_PATH, destino)
    return destino
