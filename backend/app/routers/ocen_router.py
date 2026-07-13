"""OCEN-compliant credit-assessment endpoint for LSPs on ONDC.

Treated as an UNTRUSTED-INPUT boundary: strict Pydantic validation and auth required. Returns an
OCEN-shaped assessment. Uses the same single-model pipeline as /score."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from ..auth import require_role
from ..orchestrator import orchestrate
from ..persistence import record_score
from ..schemas import OCENAssessRequest, OCENAssessResponse
from ..scoring_service import score_borrower

router = APIRouter(prefix="/ocen", tags=["ocen"])

DISCLAIMER = ("AI-assisted assessment for underwriter decision support (human-in-the-loop). "
              "Not an automated credit sanction. Complies with RBI/DPDP consent requirements.")


@router.post("/assess", response_model=OCENAssessResponse)
async def assess(req: OCENAssessRequest, user: dict = Depends(require_role("rm"))):
    identifiers = req.borrower.model_dump()
    bundle = await orchestrate(identifiers)
    result = score_borrower(bundle["features"], bundle["availability"], include_scorecard=False)
    card = result["health_card"]
    record_score(identifiers, result, bundle["features"], bundle["availability"],
                 mode="origination", note=f"ocen:{req.lsp_id}")

    sub_scores = {p["pillar"]: p["sub_score"] for p in card["pillars"]}
    return OCENAssessResponse(
        assessment_id=f"OCEN-{uuid.uuid4().hex[:16]}",
        borrower_urn=req.borrower.urn,
        credit_score=card["composite_score"],
        probability_of_default=card["pd"],
        risk_tier=card["tier_label"],
        recommended_action=card["action"],
        sub_scores=sub_scores,
        reason_codes=card["reason_codes"],
        confidence=card["confidence"],
        model_version=card["model_version"],
        disclaimer=DISCLAIMER,
    )
