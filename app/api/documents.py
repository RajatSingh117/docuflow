from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.database import get_db
from app.models.document import Document, UploadStatus
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.schemas.document import DocumentResponse
from app.api.deps import get_current_user, require_manager_or_admin, require_any_authenticated
from app.services.document_service import (
    validate_file_content,
    calculate_sha256,
    save_uploaded_file,
    check_duplicate_document,
)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("", response_model=List[DocumentResponse])
def list_documents(
    search: Optional[str] = Query(None, description="Search by original filename"),
    file_type: Optional[str] = Query(None, description="Filter by file type (pdf, csv, xlsx, etc.)"),
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve catalog of uploaded documents with search and filtering."""
    query = db.query(Document)

    if search:
        query = query.filter(Document.original_filename.ilike(f"%{search}%"))
    if file_type:
        query = query.filter(Document.file_type == file_type.lower())

    docs = query.order_by(Document.uploaded_at.desc()).offset(skip).limit(limit).all()

    # Annotate uploader names
    results = []
    for d in docs:
        resp = DocumentResponse(
            id=d.id,
            original_filename=d.original_filename,
            file_type=d.file_type,
            file_size=d.file_size,
            checksum=d.checksum,
            upload_status=d.upload_status,
            uploaded_by=d.uploaded_by,
            uploader_name=d.uploader.name if d.uploader else "System",
            uploaded_at=d.uploaded_at
        )
        results.append(resp)
    return results


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """
    Secure document upload endpoint.
    Validates MIME/magic bytes, size limit, calculates SHA-256, stores file with randomized name.
    """
    content = await file.read()
    canonical_type = validate_file_content(file.filename or "", content)
    checksum = calculate_sha256(content)

    # Check for duplicate file using SHA-256
    existing = check_duplicate_document(db, checksum)
    if existing:
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate document detected. This file has already been uploaded as '{existing.original_filename}' (Document #{existing.id})."
        )

    orig_name, stored_name, storage_ref, file_size = save_uploaded_file(file, content)

    doc = Document(
        uploaded_by=current_user.id,
        original_filename=orig_name,
        stored_filename=stored_name,
        file_type=canonical_type,
        file_size=file_size,
        checksum=checksum,
        storage_reference=storage_ref,
        upload_status=UploadStatus.STORED
    )
    db.add(doc)
    db.flush()

    # Record Audit Log
    client_ip = request.client.host if request and request.client else "unknown"
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        entity_type="Document",
        entity_id=doc.id,
        new_values={
            "filename": orig_name,
            "type": canonical_type,
            "size": file_size,
            "checksum": checksum
        },
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()
    db.refresh(doc)

    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        checksum=doc.checksum,
        upload_status=doc.upload_status,
        uploaded_by=doc.uploaded_by,
        uploader_name=current_user.name,
        uploaded_at=doc.uploaded_at
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Retrieve metadata for a specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return DocumentResponse(
        id=doc.id,
        original_filename=doc.original_filename,
        file_type=doc.file_type,
        file_size=doc.file_size,
        checksum=doc.checksum,
        upload_status=doc.upload_status,
        uploaded_by=doc.uploaded_by,
        uploader_name=doc.uploader.name if doc.uploader else "System",
        uploaded_at=doc.uploaded_at
    )


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user: User = Depends(require_any_authenticated),
    db: Session = Depends(get_db)
):
    """Securely download the original document with strict path traversal protection."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    file_path = Path(doc.storage_reference).resolve()
    # Path traversal protection: Ensure path is strictly within storage directory
    storage_root = Path(settings.STORAGE_DIR).resolve()
    if not str(file_path).startswith(str(storage_root)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path traversal.")

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file missing on disk.")

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type="application/octet-stream"
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: int,
    current_user: User = Depends(require_manager_or_admin),
    db: Session = Depends(get_db)
):
    """Delete a document and clean up disk storage."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Remove file from disk if present
    file_path = Path(doc.storage_reference)
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_DELETED",
        entity_type="Document",
        entity_id=doc.id,
        old_values={"filename": doc.original_filename, "checksum": doc.checksum}
    )
    db.add(audit)
    db.delete(doc)
    db.commit()
    return {"message": f"Document '{doc.original_filename}' deleted successfully."}
