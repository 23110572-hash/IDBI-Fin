"""Electricity-bill OCR behind an interface. AWS Textract in production; a local regex extractor
for standalone dev so the app runs without live AWS."""
from __future__ import annotations

import re

from .config import get_settings

_settings = get_settings()

_UNITS_RE = re.compile(r"Units\s+Consumed[:\s]+([\d,]+)", re.IGNORECASE)
_LOAD_RE = re.compile(r"Sanctioned\s+Load[:\s]+([\d.]+)", re.IGNORECASE)
_AMOUNT_RE = re.compile(r"Bill\s+Amount[:\s]+Rs\.?\s*([\d,]+\.?\d*)", re.IGNORECASE)


def extract_bill(content: bytes, content_type: str = "text/plain") -> dict:
    """Return structured fields from an uploaded power bill."""
    if _settings.use_textract:
        return _textract_extract(content, content_type)
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


def _textract_extract(content: bytes, content_type: str) -> dict:  # pragma: no cover
    """AWS Textract path (used when MSME_USE_TEXTRACT=true and creds are configured)."""
    import boto3

    client = boto3.client("textract")
    resp = client.analyze_document(Document={"Bytes": content},
                                   FeatureTypes=["FORMS"])
    text = " ".join(b.get("Text", "") for b in resp.get("Blocks", []) if b.get("BlockType") == "LINE")
    return _local_extract(text.encode())
