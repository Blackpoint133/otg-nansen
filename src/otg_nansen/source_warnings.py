"""Strict warning classification and sanitized audit summaries."""

from __future__ import annotations

import re
from typing import Iterable

from .client import PaginationPageMetadata
from .errors import SourceWarningError

NON_EXCHANGE_BREAKDOWN_UNAVAILABLE = "NON_EXCHANGE_BREAKDOWN_UNAVAILABLE"
UNKNOWN = "UNKNOWN"

# Full-string semantic forms only. The allow rule requires the warning to state
# both that CEX/DEX breakdowns are unavailable and that this applies outside
# the exchange label. Arbitrary surrounding warning text is not accepted.
_BENIGN_FORMS = (
    re.compile(r"(?:cex\s*(?:/|and)\s*dex|dex\s*(?:/|and)\s*cex)\s*(?:flow\s+)?(?:breakdown(?:\s+fields?)?|breakdowns|fields|metrics)\s+(?:are\s+)?(?:only\s+)?(?:available\s+for\s+)?exchange\s+labels?\s+(?:and\s+)?(?:are\s+)?null\s+for\s+(?:all\s+)?non[- ]exchange\s+labels?\.?", re.I),
    re.compile(r"(?:cex\s*(?:/|and)\s*dex|dex\s*(?:/|and)\s*cex)\s*(?:flow\s+)?(?:breakdown(?:\s+fields?)?|breakdowns|fields|metrics)\s+(?:are\s+)?(?:unavailable|null)\s+for\s+non[- ]exchange\s+labels?\.?", re.I),
    re.compile(r"(?:cex\s*(?:/|and)\s*dex|dex\s*(?:/|and)\s*cex)\s*(?:flow\s+)?(?:breakdown(?:\s+fields?)?|breakdowns|fields|metrics)\s+(?:are\s+)?null\s+for\s+non[- ]exchange\s+labels?\.?", re.I),
)


def _category(raw: object) -> str:
    if not isinstance(raw, str):
        return UNKNOWN
    text = " ".join(raw.split())
    if any(pattern.fullmatch(text) for pattern in _BENIGN_FORMS):
        return NON_EXCHANGE_BREAKDOWN_UNAVAILABLE
    return UNKNOWN


def classify_page_warnings(endpoint: str, flow_label: str | None, page: PaginationPageMetadata) -> dict:
    """Return fields safe for durable audit; never returns source text."""
    categories = sorted({_category(item) for item in page.warnings})
    summary = {"page": page.page, "warning_count": len(page.warnings), "categories": categories}
    allowed = endpoint == "flows" and flow_label == "smart_money"
    if any(category == UNKNOWN for category in categories) or (categories and (not allowed or categories != [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE])):
        raise SourceWarningError(endpoint, page.page, len(page.warnings), categories or [UNKNOWN])
    return summary


def summarize_page_warnings(endpoint: str, flow_label: str | None, pages: Iterable[PaginationPageMetadata]) -> list[dict]:
    """Classify each warned page and return a sanitized ordered audit list."""
    return [classify_page_warnings(endpoint, flow_label, page) for page in pages if page.warnings]


def sanitized_unknown_summaries(pages: Iterable[PaginationPageMetadata]) -> list[dict]:
    """Build a safe fallback summary if classification itself fails."""
    return [
        {"page": page.page, "warning_count": len(page.warnings), "categories": [UNKNOWN]}
        for page in pages if page.warnings
    ]
