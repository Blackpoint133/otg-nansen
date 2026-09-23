"""Exact source-warning fingerprints and sanitized audit summaries."""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable, Mapping

from .client import PaginationPageMetadata
from .errors import SourceWarningError

NON_EXCHANGE_BREAKDOWN_UNAVAILABLE = "NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"
UNKNOWN = "UNKNOWN"

# TGM Flows; smart_money; observed 2026-09-23. Meaning validated through
# documented breakdown behavior; exact wording intentionally not retained.
KNOWN_FLOW_WARNING_FINGERPRINTS = {
    "50a9e595fb2d539dbf5aade57b0dfba8b440f00841933c87a3335644dca23912": NON_EXCHANGE_BREAKDOWN_UNAVAILABLE,
}

_BREAKDOWN_FIELDS = (
    "total_inflows_cex",
    "total_inflows_dex",
    "total_outflows_cex",
    "total_outflows_dex",
)


def warning_fingerprint(raw: object) -> str | None:
    """Hash the exact decoded UTF-8 source string, without normalization."""
    if not isinstance(raw, str):
        return None
    return sha256(raw.encode("utf-8")).hexdigest()


def classify_warning(raw: object, endpoint: str, flow_label: str | None, *, allowlist: Mapping[str, str] | None = None) -> str:
    """Classify one warning; allowlist injection exists for synthetic tests."""
    fingerprints = KNOWN_FLOW_WARNING_FINGERPRINTS if allowlist is None else allowlist
    category = fingerprints.get(warning_fingerprint(raw) or "", UNKNOWN)
    if category == NON_EXCHANGE_BREAKDOWN_UNAVAILABLE and (endpoint != "flows" or flow_label != "smart_money"):
        return UNKNOWN
    return category if category in {NON_EXCHANGE_BREAKDOWN_UNAVAILABLE, UNKNOWN} else UNKNOWN


def classify_page_warnings(endpoint: str, flow_label: str | None, page: PaginationPageMetadata) -> dict:
    """Return fields safe for durable audit; never returns source text."""
    categories = sorted({classify_warning(item, endpoint, flow_label) for item in page.warnings})
    summary = {"page": page.page, "warning_count": len(page.warnings), "categories": categories}
    if UNKNOWN in categories:
        raise SourceWarningError(endpoint, page.page, len(page.warnings), categories)
    return summary


def summarize_page_warnings(endpoint: str, flow_label: str | None, pages: Iterable[PaginationPageMetadata]) -> list[dict]:
    """Classify each warned page and return a sanitized ordered audit list."""
    summaries = []
    for page in pages:
        if page.warnings:
            summaries.append(classify_page_warnings(endpoint, flow_label, page))
    return summaries


def validate_warning_structure(summaries: Iterable[dict], models: Iterable[object], *, endpoint: str = "flows") -> None:
    """Require observed normalized records to support the documented null breakdown semantics."""
    benign = [item for item in summaries if NON_EXCHANGE_BREAKDOWN_UNAVAILABLE in item.get("categories", ())]
    if not benign:
        return
    records = list(models)
    valid = bool(records) and all(all(getattr(record, field, None) is None for field in _BREAKDOWN_FIELDS) for record in records)
    if not valid:
        page = benign[0].get("page", 1)
        count = sum(int(item.get("warning_count", 0)) for item in benign)
        raise SourceWarningError(endpoint, page, count, [UNKNOWN])


def sanitized_unknown_summaries(pages: Iterable[PaginationPageMetadata]) -> list[dict]:
    """Build a safe fallback summary if classification itself fails."""
    return [
        {"page": page.page, "warning_count": len(page.warnings), "categories": [UNKNOWN]}
        for page in pages if page.warnings
    ]
