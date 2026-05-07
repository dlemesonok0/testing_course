import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from app.config import UPLOAD_DIR
from app.schemas import MAX_PHOTO_COUNT


def save_upload(file: UploadFile | None) -> str | None:
    if file is None or not file.filename:
        return None

    suffix = Path(file.filename).suffix
    filename = f"{uuid4().hex}{suffix}"
    destination = UPLOAD_DIR / filename
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return filename


def validate_image_uploads(files: list[UploadFile] | None, *, max_count: int = MAX_PHOTO_COUNT) -> list[UploadFile]:
    normalized = [file for file in (files or []) if getattr(file, "filename", None)]
    if len(normalized) > max_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Нельзя добавить более {max_count} фотографий",
        )
    invalid_files = [
        file.filename or "upload"
        for file in normalized
        if file.content_type and not file.content_type.startswith("image/")
    ]
    if invalid_files:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Разрешены только изображения: {', '.join(invalid_files)}",
        )
    return normalized


def save_uploads(files: list[UploadFile] | None) -> list[str]:
    if not files:
        return []
    return [saved for saved in (save_upload(file) for file in files) if saved is not None]


def build_asset_url(path: str) -> str:
    if path.startswith(("http://", "https://", "/uploads/")):
        return path
    return f"/uploads/{path}"


def normalize_storage_path(url_or_path: str) -> str:
    """Removes the /uploads/ prefix if present to store only the filename for local assets."""
    if url_or_path.startswith("/uploads/"):
        return url_or_path[len("/uploads/"):]
    return url_or_path
