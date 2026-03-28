from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path
from typing import Any
from uuid import UUID
from sqlalchemy import select

from fastapi import UploadFile
from sqlalchemy.orm import Session

from pypdf import PdfReader
from docx import Document

from app.db.models.orchestrator_session import OrchestratorSession
from app.db.models.uploaded_file import UploadedFile


BASE_DIR = Path(__file__).resolve().parents[2]
UPLOADS_ROOT = BASE_DIR / "storage" / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

LEGAL_KEYWORDS = {
    "contrato",
    "cláusula",
    "clausula",
    "arrendamiento",
    "arrendador",
    "arrendatario",
    "locador",
    "locatario",
    "partes",
    "obligaciones",
    "vigencia",
    "penalidad",
    "penalidades",
    "jurisdicción",
    "jurisdiccion",
    "resolución",
    "resolucion",
    "incumplimiento",
    "anexo",
    "firma",
    "firmas",
    "empleador",
    "trabajador",
    "prestación",
    "prestacion",
    "servicios",
    "confidencialidad",
    "nda",
    "adenda",
    "compraventa",
    "mandato",
    "representación",
    "representacion",
    "ley aplicable",
}

NON_LEGAL_STRONG_KEYWORDS = {
    "teorema",
    "integral",
    "derivada",
    "matriz",
    "álgebra",
    "algebra",
    "geometría",
    "geometria",
    "física",
    "fisica",
    "química",
    "quimica",
    "algoritmo",
    "programación competitiva",
    "programacion competitiva",
}


def _sanitize_filename(filename: str) -> str:
    cleaned = (filename or "archivo").strip()
    cleaned = cleaned.replace("\\", "_").replace("/", "_")
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "", cleaned)
    return cleaned or "archivo"


def _extract_extension(filename: str) -> str:
    return Path(filename or "").suffix.lower().strip()


def _extract_pdf_text(path: Path, max_chars: int = 6000) -> str:
    reader = PdfReader(str(path))
    chunks: list[str] = []

    for page in reader.pages[:3]:
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(text.strip())
        joined = "\n".join(chunks)
        if len(joined) >= max_chars:
            return joined[:max_chars]

    return "\n".join(chunks)[:max_chars]


def _extract_docx_text(path: Path, max_chars: int = 6000) -> str:
    doc = Document(str(path))
    chunks: list[str] = []

    for p in doc.paragraphs[:80]:
        text = (p.text or "").strip()
        if text:
            chunks.append(text)
        joined = "\n".join(chunks)
        if len(joined) >= max_chars:
            return joined[:max_chars]

    return "\n".join(chunks)[:max_chars]


def _extract_txt_text(path: Path, max_chars: int = 6000) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return raw[:max_chars]


def extract_text_sample(path: Path, extension: str, max_chars: int = 6000) -> str:
    if extension == ".pdf":
        return _extract_pdf_text(path, max_chars=max_chars)
    if extension == ".docx":
        return _extract_docx_text(path, max_chars=max_chars)
    if extension == ".txt":
        return _extract_txt_text(path, max_chars=max_chars)
    return ""


def classify_legal_document(text: str) -> dict[str, Any]:
    normalized = (text or "").lower()

    legal_hits = sum(1 for kw in LEGAL_KEYWORDS if kw in normalized)
    non_legal_hits = sum(1 for kw in NON_LEGAL_STRONG_KEYWORDS if kw in normalized)

    if legal_hits >= 2:
        return {
            "validation_status": "accepted",
            "validation_label": "contract_legal",
            "validation_reason": "El archivo parece corresponder a un documento legal o contractual.",
        }

    if non_legal_hits >= 2 and legal_hits == 0:
        return {
            "validation_status": "rejected",
            "validation_label": "non_legal",
            "validation_reason": "El archivo no parece corresponder a un documento legal o contractual.",
        }

    return {
        "validation_status": "rejected",
        "validation_label": "uncertain",
        "validation_reason": "No se pudo validar con suficiente confianza que el archivo sea un documento legal o contractual.",
    }


def upload_file_for_session(
    db: Session,
    *,
    session_id: UUID,
    file: UploadFile,
) -> dict[str, Any]:
    session_obj = db.query(OrchestratorSession).filter(OrchestratorSession.id == session_id).first()
    if not session_obj:
        raise ValueError("SESSION_NOT_FOUND")

    original_filename = file.filename or "archivo"
    file_extension = _extract_extension(original_filename)

    if file_extension not in ALLOWED_EXTENSIONS:
        raise ValueError("UNSUPPORTED_FILE_TYPE")

    file_id = uuid.uuid4()
    safe_filename = _sanitize_filename(original_filename)
    stored_filename = f"{file_id}__{safe_filename}"

    session_dir = UPLOADS_ROOT / str(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    destination = session_dir / stored_filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    size_bytes = destination.stat().st_size
    mime_type = getattr(file, "content_type", None)

    text_sample = extract_text_sample(destination, file_extension)
    validation = classify_legal_document(text_sample)

    uploaded = UploadedFile(
        id=file_id,
        session_id=session_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        file_extension=file_extension,
        mime_type=mime_type,
        size_bytes=size_bytes,
        storage_path=str(destination),
        upload_status="uploaded",
        validation_status=validation["validation_status"],
        validation_label=validation["validation_label"],
        validation_reason=validation["validation_reason"],
    )

    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)

    is_accepted = uploaded.validation_status == "accepted"

    return {
        "ok": is_accepted,
        "message": (
            "Archivo validado correctamente."
            if is_accepted
            else "El archivo no parece corresponder a un contrato o documento relacionado con este análisis legal."
        ),
        "file": uploaded,
        "ui_context": {
            "input_file_name": uploaded.original_filename if is_accepted else None,
            "uploaded_file_id": uploaded.id if is_accepted else None,
            "file_uploaded": is_accepted,
            "file_validation_status": uploaded.validation_status,
        },
    }

def list_uploaded_files_by_session(
    db: Session,
    *,
    session_id: UUID,
    only_accepted: bool = False,
) -> list[UploadedFile]:
    session_obj = (
        db.query(OrchestratorSession)
        .filter(OrchestratorSession.id == session_id)
        .first()
    )
    if not session_obj:
        raise ValueError("SESSION_NOT_FOUND")

    stmt = (
        select(UploadedFile)
        .where(UploadedFile.session_id == session_id)
        .order_by(UploadedFile.created_at.desc())
    )

    if only_accepted:
        stmt = stmt.where(UploadedFile.validation_status == "accepted")

    return list(db.execute(stmt).scalars().all())

def get_uploaded_file_by_id(
    db: Session,
    *,
    file_id: UUID,
) -> UploadedFile | None:
    return (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id)
        .first()
    )