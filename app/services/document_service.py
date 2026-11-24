import os
import uuid
import hashlib
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from app.config import settings
from app.models.document import Document
from sqlalchemy.orm import Session

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".png": "png",
    ".tif": "tiff",
    ".tiff": "tiff",
}


def calculate_sha256(content: bytes) -> str:
    """Calculate SHA-256 hex digest of file content."""
    hasher = hashlib.sha256()
    hasher.update(content)
    return hasher.hexdigest()


def validate_file_content(filename: str, content: bytes) -> str:
    """Validate file content against magic bytes and structure to prevent spoofing."""
    if not content or len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded. Files with 0 bytes are rejected."
        )

    # Size validation
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum upload size limit of {settings.MAX_UPLOAD_SIZE_MB} MB."
        )

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: PDF, CSV, XLSX, JPG, PNG, TIFF."
        )

    canonical_type = SUPPORTED_EXTENSIONS[ext]

    # Validate Magic Bytes / Signatures
    if canonical_type == "pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted PDF file. Missing valid PDF signature."
            )
    elif canonical_type == "png":
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted PNG file. Missing PNG header."
            )
    elif canonical_type == "jpg":
        if not (content.startswith(b"\xff\xd8\xff") or content.startswith(b"\xff\xd8")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted JPEG image. Missing JPEG SOI header."
            )
    elif canonical_type == "tiff":
        if not (content.startswith(b"II*\x00") or content.startswith(b"MM\x00*")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted TIFF image. Missing TIFF header."
            )
    elif canonical_type == "xlsx":
        # XLSX is a ZIP package starting with PK\x03\x04
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted Excel spreadsheet. Missing ZIP/OpenXML signature."
            )
    elif canonical_type == "csv":
        # CSV should be decodable text
        try:
            content[:4096].decode("utf-8")
        except UnicodeDecodeError:
            try:
                content[:4096].decode("latin-1")
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid CSV file. Content is not valid text."
                )

    return canonical_type


def save_uploaded_file(file: UploadFile, content: bytes) -> Tuple[str, str, str, int]:
    """
    Save validated file using randomized UUID to prevent collisions and path traversal.
    Returns: (original_filename, stored_filename, storage_path, file_size)
    """
    ext = Path(file.filename or "upload").suffix.lower()
    random_id = uuid.uuid4().hex
    stored_filename = f"{random_id}{ext}"
    destination_path = settings.uploads_path / stored_filename

    # Write file safely
    with open(destination_path, "wb") as f:
        f.write(content)

    return (
        file.filename or f"document_{random_id[:8]}{ext}",
        stored_filename,
        str(destination_path),
        len(content)
    )


def check_duplicate_document(db: Session, checksum: str) -> Optional[Document]:
    """Find existing document matching SHA-256 checksum."""
    return db.query(Document).filter(Document.checksum == checksum).first()
