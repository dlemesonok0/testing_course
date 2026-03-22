import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
DB_PATH = Path(os.getenv("RECIPE_BOOK_DB_PATH", BASE_DIR / "recipe_book.db"))
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
