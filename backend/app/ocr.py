"""Electricity-bill OCR. A lightweight regex extractor pulls the units-consumed, sanctioned load,
and bill amount from an uploaded power bill (text). Kept behind a small interface so a heavier OCR
engine can be swapped in later without touching callers."""
from __future__ import annotations

import re

_UNITS_RE = re.compile(r"Units\s+Consumed[:\s]+([\d,]+)", re.IGNORECASE)
_LOAD_RE = re.compile(r"Sanctioned\s+Load[:\s]+([\d.]+)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"Bill\s+Amount[:\s]+Rs\.?\s*([\d,]+\.?\d*)", re.IGNORECASE)


def extract_bill(content: bytes, content_type: str = "text/plain") -> dict:
    """Return structured fields from an uploaded power bill."""
    return _local_extract(content)


def _local_extract(content: bytes) -> dict:
    text = content.decode("utf-8", errors="ignore")
    units = _UNITS_RE.search(text)
    load = _LOAD_RE.search(text)
    amount = _AMOUNT_RE.search(text)

    def _num(m):
        return float(m.group(1).replace(",", "")) if m else None

    kwh = _num(units)
    load_kw = _num(load)
    return {
        "engine": "local_regex",
        "units_consumed_kwh": kwh,
        "sanctioned_load_kw": load_kw,
        "bill_amount": _num(amount),
        "extracted_ok": kwh is not None,
    }
