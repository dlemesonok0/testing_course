import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import UPLOAD_DIR


def save_upload(file: UploadFile | None) -> str | None:
    if file is None or not file.filename:
        return None

    suffix = Path(file.filename).suffix
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename


def save_uploads(files: list[UploadFile] | None) -> list[str]:
    if not files:
        return []
    return [saved for saved in (save_upload(file) for file in files) if saved is not None]
