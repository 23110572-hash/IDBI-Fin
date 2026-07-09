"""Mode A — origination scoring. Orchestrate -> data-quality gate -> single-model score ->
append to ledger -> Health Card. Also portfolio + borrower history + ledger reproducibility."""
from __future__ import annotations

import datetime as dt
import time

from fastapi import APIRouter, Depends, HTTPException

from ..auth import current_user, require_role
from ..orchestrator import orchestrate
from ..persistence import get_history, get_ledger_entry, get_portfolio, record_score
from ..schemas import ScoreRequest, ScoreResponse
from ..scoring_service import data_quality_report, score_borrower

router = APIRouter(tags=["scoring"])


@router.post("/score", response_model=ScoreResponse)
async def score(req: ScoreRequest, user: dict = Depends(require_role("rm"))):
    started = time.perf_counter()
    identifiers = req.identifiers.model_dump()

    bundle = await orchestrate(identifiers, consent_token=req.consent_id)
    dq = data_quality_report(bundle["features"], bundle["availability"])
    if not dq["passed"]:
        raise HTTPException(status_code=422, detail={
            "message": "Data-quality gate failed (critical source AA missing or coverage too low).",
            "data_quality": dq})

    result = score_borrower(bundle["features"], bundle["availability"],
                            include_scorecard=req.include_scorecard)
    record_score(identifiers, result, bundle["features"], bundle["availability"],
                 mode="origination", consent_id=req.consent_id)
    latency_ms = round((time.perf_counter() - started) * 1000)

    return ScoreResponse(
        score_id=result["score_id"], urn=req.identifiers.urn,
        business_name=req.identifiers.business_name, mode="origination",
        latency_ms=latency_ms, health_card=result["health_card"],
        scorecard=result.get("scorecard"),
        data_quality={**dq, "connector_diagnostics": bundle["diagnostics"]},
        created_at=dt.datetime.now(dt.UTC).isoformat())


@router.get("/portfolio")
async def portfolio(user: dict = Depends(current_user)):
    return {"borrowers": get_portfolio()}


@router.get("/borrower/{urn}")
async def borrower_history(urn: str, user: dict = Depends(current_user)):
    history = get_history(urn)
    if not history:
        raise HTTPException(status_code=404, detail="No scores for this borrower")
    return {"urn": urn, "history": history, "latest": history[-1]}


@router.get("/score/{score_id}")
async def ledger_entry(score_id: str, user: dict = Depends(require_role("credit_officer"))):
    """Reproducibility: full feature snapshot + model version for an audited decision."""
    entry = get_ledger_entry(score_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Score not found")
    return entry
