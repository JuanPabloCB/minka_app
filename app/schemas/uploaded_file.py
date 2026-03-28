from __future__ import annotations

from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel


ValidationStatus = Literal["pending", "accepted", "rejected"]


class UploadedFileOut(BaseModel):
    id: UUID
    session_id: UUID

    original_filename: str
    stored_filename: str
    file_extension: str
    mime_type: str | None = None
    size_bytes: int
    storage_path: str

    upload_status: str
    validation_status: ValidationStatus
    validation_label: str | None = None
    validation_reason: str | None = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UploadFileResponse(BaseModel):
    ok: bool
    message: str
    file: UploadedFileOut | None = None
    ui_context: dict | None = None

class UploadedFileListItemOut(BaseModel):
    id: UUID
    session_id: UUID
    original_filename: str
    file_extension: str
    mime_type: str | None = None
    size_bytes: int
    validation_status: ValidationStatus
    validation_label: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True