"""Consent lifecycle (DPDP): requested -> active -> revoked/expired. Immutable Consent Registry."""
from __future__ import annotations

import datetime as dt
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..auth import current_user
from ..db import session_scope
from ..models import ConsentRecord
from ..persistence import mask_gstin, mask_pan
from ..schemas import ConsentRequest, ConsentResponse

router = APIRouter(prefix="/consent", tags=["consent"])


def _to_response(c: ConsentRecord) -> ConsentResponse:
    return ConsentResponse(
        consent_id=c.consent_id, consent_handle=c.consent_handle, status=c.status,
        purpose=c.purpose, urn=c.urn, fi_types=c.fi_types,
        created_at=c.created_at.isoformat(), expires_at=c.expires_at.isoformat())


@router.post("", response_model=ConsentResponse)
async def create_consent(req: ConsentRequest, user: dict = Depends(current_user)):
    now = dt.datetime.now(dt.UTC)
    consent_id = f"CN-{uuid.uuid4().hex[:16]}"
    handle = f"AA-{uuid.uuid4().hex[:20]}"  # Sahamati-style consent handle
    with session_scope() as s:
        rec = ConsentRecord(
            consent_id=consent_id, consent_handle=handle, urn=req.identifiers.urn,
            pan_masked=mask_pan(req.identifiers.pan), gstin_masked=mask_gstin(req.identifiers.gstin),
            purpose=req.purpose, fi_types=req.fi_types, status="ACTIVE",
            created_at=now, expires_at=now + dt.timedelta(days=req.duration_days))
        s.add(rec)
        s.flush()
        return _to_response(rec)


@router.get("/{consent_id}", response_model=ConsentResponse)
async def get_consent(consent_id: str, user: dict = Depends(current_user)):
    with session_scope() as s:
        c = s.execute(select(ConsentRecord).where(ConsentRecord.consent_id == consent_id)).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Consent not found")
        return _to_response(c)


@router.post("/{consent_id}/revoke", response_model=ConsentResponse)
async def revoke_consent(consent_id: str, user: dict = Depends(current_user)):
    with session_scope() as s:
        c = s.execute(select(ConsentRecord).where(ConsentRecord.consent_id == consent_id)).scalar_one_or_none()
        if not c:
            raise HTTPException(status_code=404, detail="Consent not found")
        c.status = "REVOKED"
        c.revoked_at = dt.datetime.now(dt.UTC)
        s.flush()
        return _to_response(c)
