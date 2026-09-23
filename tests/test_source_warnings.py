import hashlib

import pytest

from otg_nansen.client import PaginationPageMetadata
from otg_nansen.errors import SourceWarningError
from otg_nansen.models import NormalizedFlowRecord
from otg_nansen.source_warnings import (
    NON_EXCHANGE_BREAKDOWN_UNAVAILABLE, UNKNOWN, classify_page_warnings,
    classify_warning, summarize_page_warnings, validate_warning_structure,
)


SYNTHETIC = "synthetic verified breakdown notice"
FINGERPRINTS = {hashlib.sha256(SYNTHETIC.encode("utf-8")).hexdigest(): NON_EXCHANGE_BREAKDOWN_UNAVAILABLE}


def record(**fields):
    values = dict(chain="avalanche", token_address="synthetic", date=None, price_usd=1, token_amount=1,
                  value_usd=1, holders_count=1, total_inflows_count=1, total_outflows_count=1,
                  flow_label="smart_money", bucket_end=None, is_complete=True,
                  total_inflows_cex=None, total_inflows_dex=None, total_outflows_cex=None, total_outflows_dex=None)
    values.update(fields)
    return NormalizedFlowRecord(**values)


def test_no_warnings_produces_empty_audit_list():
    assert summarize_page_warnings("flows", "smart_money", [PaginationPageMetadata(1, ())]) == []


def test_exact_synthetic_fingerprint_is_candidate_benign():
    assert classify_warning(SYNTHETIC, "flows", "smart_money", allowlist=FINGERPRINTS) == NON_EXCHANGE_BREAKDOWN_UNAVAILABLE


@pytest.mark.parametrize("changed", [
    "synthetic verified breakdown notice!",
    "synthetic verified  breakdown notice",
    "Synthetic verified breakdown notice",
    "synthetic verified breakdown notice?",
    "unrelated synthetic source warning",
])
def test_any_source_text_change_is_unknown(changed):
    assert classify_warning(changed, "flows", "smart_money", allowlist=FINGERPRINTS) == UNKNOWN


@pytest.mark.parametrize("endpoint,label", [("dex-trades", None), ("flows", "exchange")])
def test_exact_hash_in_wrong_context_is_unknown(endpoint, label):
    assert classify_warning(SYNTHETIC, endpoint, label, allowlist=FINGERPRINTS) == UNKNOWN


def test_unlisted_fingerprint_is_unknown():
    assert classify_warning(SYNTHETIC, "flows", "smart_money", allowlist={}) == UNKNOWN


def test_page_summary_is_sanitized_and_duplicate_count_is_preserved(monkeypatch):
    import otg_nansen.source_warnings as warning_policy
    monkeypatch.setattr(warning_policy, "KNOWN_FLOW_WARNING_FINGERPRINTS", FINGERPRINTS)
    page = PaginationPageMetadata(4, (SYNTHETIC, SYNTHETIC))
    summary = classify_page_warnings("flows", "smart_money", page)
    assert summary == {"page": 4, "warning_count": 2, "categories": [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE]}
    assert SYNTHETIC not in str(summary)


def test_unknown_mixed_with_exact_candidate_rejects_whole_page_without_echo():
    page = PaginationPageMetadata(2, (SYNTHETIC, "unrelated private warning"))
    with pytest.raises(SourceWarningError) as error:
        classify_page_warnings("flows", "smart_money", page)
    assert error.value.warning_count == 2 and UNKNOWN in error.value.categories
    assert "unrelated private warning" not in str(error.value)


def test_structural_guard_accepts_all_null_breakdown_fields():
    validate_warning_structure([{"page": 1, "warning_count": 1, "categories": [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE]}], [record()])


@pytest.mark.parametrize("field", ["total_inflows_cex", "total_inflows_dex", "total_outflows_cex", "total_outflows_dex"])
def test_structural_guard_rejects_each_non_null_breakdown_field(field):
    summary = [{"page": 1, "warning_count": 1, "categories": [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE]}]
    with pytest.raises(SourceWarningError) as error:
        validate_warning_structure(summary, [record(**{field: 1})])
    assert error.value.categories == (UNKNOWN,)


def test_structural_guard_rejects_empty_records_for_benign_warning():
    with pytest.raises(SourceWarningError):
        validate_warning_structure([{"page": 1, "warning_count": 1, "categories": [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE]}], [])
