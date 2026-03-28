from uuid import UUID
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.deps import get_db
from app.schemas.uploaded_file import UploadFileResponse, UploadedFileListItemOut
from app.services.file_intake_service import (
    upload_file_for_session,
    list_uploaded_files_by_session,
    get_uploaded_file_by_id,
)

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload/{session_id}", response_model=UploadFileResponse)
def upload_file_endpoint(
    session_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    try:
        result = upload_file_for_session(
            db,
            session_id=session_id,
            file=file,
        )
        return UploadFileResponse(**result)

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Session not found")

        if str(e) == "UNSUPPORTED_FILE_TYPE":
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: pdf, docx, txt",
            )

        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")

    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected file processing error")
    
@router.get("/by-session/{session_id}", response_model=list[UploadedFileListItemOut])
def list_files_by_session(
    session_id: UUID,
    only_accepted: bool = True,
    db: Session = Depends(get_db),
):
    try:
        files = list_uploaded_files_by_session(
            db,
            session_id=session_id,
            only_accepted=only_accepted,
        )
        return [UploadedFileListItemOut.model_validate(f) for f in files]

    except ValueError as e:
        if str(e) == "SESSION_NOT_FOUND":
            raise HTTPException(status_code=404, detail="Session not found")
        raise HTTPException(status_code=400, detail="Bad request")

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    

@router.get("/download/{file_id}")
def download_file(
    file_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        uploaded_file = get_uploaded_file_by_id(db, file_id=file_id)

        if not uploaded_file:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_path = Path(uploaded_file.storage_path)

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Stored file not found on disk")

        return FileResponse(
            path=str(file_path),
            filename=uploaded_file.original_filename,
            media_type=uploaded_file.mime_type or "application/octet-stream",
        )

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")
    
@router.get("/preview/{file_id}")
def preview_file(
    file_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        uploaded_file = get_uploaded_file_by_id(db, file_id=file_id)

        if not uploaded_file:
            raise HTTPException(status_code=404, detail="Uploaded file not found")

        file_path = Path(uploaded_file.storage_path)

        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Stored file not found on disk")

        return FileResponse(
            path=str(file_path),
            media_type=uploaded_file.mime_type or "application/octet-stream",
        )

    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Database error")