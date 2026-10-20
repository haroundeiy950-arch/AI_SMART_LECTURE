import shutil
from datetime import datetime
from pathlib import Path

from config import BACKUPS_DIR, DATABASE_PATH


def create_database_backup() -> Path:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = BACKUPS_DIR / f"security_system_{timestamp}.db"
    if not DATABASE_PATH.exists():
        raise FileNotFoundError("Database file does not exist yet.")
    shutil.copy2(DATABASE_PATH, destination)
    return destination
