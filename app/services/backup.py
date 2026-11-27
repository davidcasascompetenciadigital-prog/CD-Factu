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


def listar_backups():
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(BACKUP_DIR.glob("backup_*.db"), reverse=True)


def restaurar_backup(path: Path) -> bool:
    """Restaura la BD desde un archivo de backup. Devuelve True si OK."""
    path = Path(path)
    if not path.exists():
        return False
    # Copia de seguridad de la BD actual antes de restaurar
    try:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        seguridad = BACKUP_DIR / f"pre_restore_{stamp}.db"
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists():
            shutil.copy2(DB_PATH, seguridad)
        shutil.copy2(path, DB_PATH)
        return True
    except Exception:
        return False
