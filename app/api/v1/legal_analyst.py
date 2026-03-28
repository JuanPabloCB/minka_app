from pathlib import Path
from uuid import uuid4
from io import BytesIO
from typing import Any
import hashlib
import json

from fastapi import APIRouter, File, HTTPException, UploadFile, Form, Depends
from sqlalchemy.orm import Session
from app.services.legal_analyst_findings_service import LegalAnalystFindingsService

from app.schemas.legal_analyst import (
    LegalAnalystExecuteRequest,
    LegalAnalystExecuteResponse,
    UploadContractResponse,
    LegalAnalystStepChatRequest,
    LegalAnalystStepChatResponse,
    DetectFindingsRequest,
    DetectFindingsResponse,
)
from app.services.legal_analyst_service import LegalAnalystService
from app.services.legal_analyst_step_chat_service import LegalAnalystStepChatService

from app.db.session import get_db
from app.db.models.plan import Plan
from app.db.models.plan_step import PlanStep
from app.db.models.analyst_run import AnalystRun
from app.db.models.artifact import Artifact

router = APIRouter(prefix="/legal-analyst", tags=["Legal Analyst"])

UPLOAD_DIR = Path("storage/contracts")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("/execute", response_model=LegalAnalystExecuteResponse)
def execute_legal_analyst(payload: LegalAnalystExecuteRequest):
    service = LegalAnalystService()

    result = service.execute_analysis(
        goal_type=payload.goal_type,
        inputs=payload.inputs,
        assigned_macro_steps=payload.assigned_macro_steps,
    )

    return result


@router.post("/step-chat", response_model=LegalAnalystStepChatResponse)
def legal_analyst_step_chat(payload: LegalAnalystStepChatRequest):
    service = LegalAnalystStepChatService()
    return service.reply(
        step_id=payload.step_id,
        user_message=payload.user_message,
        goal_type=payload.goal_type,
        document_id=payload.document_id,
        filename=payload.filename,
        step_output=payload.step_output,
    )


@router.post("/upload-contract", response_model=UploadContractResponse)
async def upload_contract(
    session_id: str = Form(...),
    plan_id: str = Form(...),
    plan_step_id: str = Form(...),  # macro step visible actual
    user_id: str | None = Form(None),
    assigned_macro_steps_json: str | None = Form(None),
    selected_micro_steps_json: str | None = Form(None),
    current_micro_step: str | None = Form("load_contract"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    filename = file.filename or ""

    if not filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Formato no permitido. Solo PDF, DOCX o TXT.",
        )

    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan no encontrado.")

    step = (
        db.query(PlanStep)
        .filter(PlanStep.id == plan_step_id, PlanStep.plan_id == plan_id)
        .first()
    )
    if not step:
        raise HTTPException(status_code=404, detail="Plan step no encontrado.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    size_bytes = len(content)
    if size_bytes > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail="El archivo excede el tamaño máximo permitido de 20 MB.",
        )

    assigned_macro_steps = []
    selected_micro_steps = []

    if assigned_macro_steps_json:
        try:
            assigned_macro_steps = _safe_parse_json_list(
                assigned_macro_steps_json,
                "assigned_macro_steps_json",
            )
        except Exception:
            assigned_macro_steps = []

    if selected_micro_steps_json:
        try:
            selected_micro_steps = _safe_parse_json_list(
                selected_micro_steps_json,
                "selected_micro_steps_json",
            )
        except Exception:
            selected_micro_steps = []

    if not selected_micro_steps:
        selected_micro_steps = ["load_contract"]

    run_id = str(uuid4())
    run = AnalystRun(
        id=run_id,
        plan_step_id=plan_step_id,
        plan_id=plan_id,
        user_id=user_id,
        status="in_progress",
        current_step=1,
        run_context={
            "session_id": session_id,
            "plan_id": plan_id,
            "current_macro_step_id": plan_step_id,
            "current_macro_step_title": getattr(step, "title", None),
            "assigned_macro_steps": assigned_macro_steps,
            "selected_micro_steps": selected_micro_steps,
            "current_micro_step": current_micro_step,
            "filename": filename,
            "content_type": file.content_type or "application/octet-stream",
        },
        audit_log="Upload iniciado.",
        result={},
    )
    db.add(run)

    if hasattr(step, "status"):
        step.status = "running"

    artifact_id = str(uuid4())
    safe_filename = f"{artifact_id}_{filename}"
    destination = UPLOAD_DIR / safe_filename
    destination.write_bytes(content)
    resolved_pdf_path = str(destination.resolve())

    run_context = dict(run.run_context or {})
    run_context["pdf_path"] = resolved_pdf_path
    run_context["document_path"] = resolved_pdf_path
    run_context["file_path"] = resolved_pdf_path
    run.run_context = run_context

    sha256 = hashlib.sha256(content).hexdigest()
    size_label = _format_size(size_bytes)
    page_count = _estimate_page_count(filename, content)

    artifact = Artifact(
        id=artifact_id,
        owner_type="analyst_run",
        owner_id=run_id,
        user_id=user_id,
        kind="input",
        filename=filename,
        mime_type=file.content_type or "application/octet-stream",
        storage_provider="local",
        storage_path=str(destination),
        sha256=sha256,
        size_bytes=size_bytes,
        meta={
            "session_id": session_id,
            "plan_id": plan_id,
            "current_macro_step_id": plan_step_id,
            "current_macro_step_title": getattr(step, "title", None),
            "assigned_macro_steps": assigned_macro_steps,
            "selected_micro_steps": selected_micro_steps,
            "current_micro_step": current_micro_step,
            "size_label": size_label,
            "page_count": page_count,
            "original_filename": filename,
            "resolved_pdf_path": resolved_pdf_path,
        },
    )
    db.add(artifact)
    db.flush()

    extracted_text = _extract_text(filename=filename, content=content)
    text_length = len(extracted_text.strip()) if extracted_text else 0

    validation_status = "valid"
    message = "Contrato recibido y validado correctamente."
    is_contract_candidate = False
    document_type_guess = "unknown"

    if not extracted_text or text_length < 80:
        validation_status = "invalid"
        message = "No se pudo extraer texto suficiente del archivo."
    else:
        is_contract_candidate = _looks_like_contract(extracted_text)
        document_type_guess = "contract" if is_contract_candidate else "other"

        if not is_contract_candidate:
            validation_status = "invalid"
            message = "El archivo fue leído, pero no parece corresponder a un contrato."

    run.result = {
        "artifact_id": artifact_id,
        "document_id": artifact_id,
        "filename": filename,
        "content_type": file.content_type or "application/octet-stream",
        "size_bytes": size_bytes,
        "size_label": size_label,
        "page_count": page_count,
        "text_length": text_length,
        "validation_status": validation_status,
        "is_contract_candidate": is_contract_candidate,
        "document_type_guess": document_type_guess,
        "message": message,
        "selected_micro_steps": selected_micro_steps,
        "current_micro_step": current_micro_step,
        "current_macro_step_id": plan_step_id,
        "current_macro_step_title": getattr(step, "title", None),
        "assigned_macro_steps": assigned_macro_steps,
        "extracted_text": extracted_text,
        "pdf_path": resolved_pdf_path,
        "document_path": resolved_pdf_path,
        "file_path": resolved_pdf_path,
    }

    if validation_status == "valid":
        run.status = "done"
        run.audit_log = (run.audit_log or "") + " | Upload completado y documento validado."
        if hasattr(step, "status"):
            step.status = "done"
    else:
        run.status = "error"
        run.audit_log = (run.audit_log or "") + " | Upload completado pero documento inválido."
        if hasattr(step, "status"):
            step.status = "error"

    db.commit()
    db.refresh(run)

    return UploadContractResponse(
        ok=validation_status == "valid",
        run_id=run_id,
        artifact_id=artifact_id,
        document_id=artifact_id,
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        size_label=size_label,
        page_count=page_count,
        validation_status=validation_status,
        is_contract_candidate=is_contract_candidate,
        document_type_guess=document_type_guess,
        text_length=text_length,
        message=message,
        storage_path=str(destination),
        current_macro_step_id=plan_step_id,
        current_macro_step_title=getattr(step, "title", None),
        selected_micro_steps=selected_micro_steps,
        current_micro_step=current_micro_step,
    )

@router.post("/detect-findings", response_model=DetectFindingsResponse)
def detect_findings(payload: DetectFindingsRequest, db: Session = Depends(get_db)):
    service = LegalAnalystFindingsService(db=db)
    return service.detect_findings(
        run_id=payload.run_id,
        macro_step_id=payload.macro_step_id,
        macro_step_title=payload.macro_step_title,
        detection_mode=payload.detection_mode,
        clause_targets=payload.clause_targets,
        finding_targets=payload.finding_targets,
    )


def _format_size(size_bytes: int) -> str:
    mb = size_bytes / (1024 * 1024)
    if mb >= 1:
        return f"{mb:.1f}MB"

    kb = size_bytes / 1024
    return f"{round(kb)}KB"


def _estimate_page_count(filename: str, content: bytes) -> int | None:
    if filename.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            return len(reader.pages)
        except Exception:
            return None

    return None


def _extract_text(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()

    try:
        if ext == ".txt":
            return content.decode("utf-8", errors="ignore")

        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            chunks: list[str] = []
            for page in reader.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    chunks.append(page_text)
            return "\n".join(chunks)

        if ext == ".docx":
            from docx import Document

            doc = Document(BytesIO(content))
            paragraphs = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
            return "\n".join(paragraphs)

        return ""
    except Exception:
        return ""
    

def _safe_parse_json_list(raw_value: str | None, field_name: str) -> list[Any]:
    if not raw_value:
        return []

    try:
        parsed = json.loads(raw_value)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"El campo '{field_name}' debe ser un JSON válido.",
        )

    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=400,
            detail=f"El campo '{field_name}' debe ser una lista JSON.",
        )

    return parsed


def _looks_like_contract(text: str) -> bool:
    normalized = text.lower()

    keywords = [
        "contrato",
        "cláusula",
        "clausula",
        "partes",
        "vigencia",
        "plazo",
        "obligación",
        "obligacion",
        "resolución",
        "resolucion",
        "confidencialidad",
        "penalidad",
        "pago",
        "arrendador",
        "arrendatario",
        "proveedor",
        "cliente",
        "acuerdo",
    ]

    hits = sum(1 for kw in keywords if kw in normalized)

    numbered_structure = any(
        token in normalized
        for token in ["cláusula", "clausula", "1.", "2.", "3.", "primera", "segunda", "tercera"]
    )

    return hits >= 3 or (hits >= 2 and numbered_structure)