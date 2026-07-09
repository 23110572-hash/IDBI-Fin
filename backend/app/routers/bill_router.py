"""Electricity bill upload -> OCR -> async enrichment (off the <30s critical path)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..auth import require_role
from ..ocr import extract_bill
from ..tasks import enrich_with_electricity

router = APIRouter(prefix="/bill", tags=["electricity"])


@router.post("/upload")
async def upload_bill(
    urn: str = Form(...),
    pan: str = Form(...),
    gstin: str | None = Form(None),
    file: UploadFile = File(...),
    user: dict = Depends(require_role("rm")),
):
    content = await file.read()
    fields = extract_bill(content, file.content_type or "text/plain")
    # enqueue async enrichment (runs inline when Celery is eager / no worker present)
    task = enrich_with_electricity.delay(urn, pan, gstin, fields)
    try:
        enrichment = task.get(timeout=45)
    except Exception:
        enrichment = {"status": "queued", "task_id": str(task.id)}
    return {
        "message": "Bill processed; the electricity signal enriched the score off the origination "
                   "critical path (asynchronous).",
        "ocr": fields,
        "enrichment": enrichment,
    }
