import pytest

from otg_nansen.client import PaginationPageMetadata
from otg_nansen.errors import SourceWarningError
from otg_nansen.source_warnings import (
    NON_EXCHANGE_BREAKDOWN_UNAVAILABLE,
    UNKNOWN,
    classify_page_warnings,
    summarize_page_warnings,
)


BENIGN = "CEX/DEX breakdown fields are null for non-exchange labels."


def test_no_warnings_produces_empty_audit_list():
    assert summarize_page_warnings("flows", "smart_money", [PaginationPageMetadata(1, ())]) == []


def test_verified_smart_money_warning_is_sanitized():
    result = classify_page_warnings("flows", "smart_money", PaginationPageMetadata(1, (BENIGN,)))
    assert result == {"page": 1, "warning_count": 1, "categories": [NON_EXCHANGE_BREAKDOWN_UNAVAILABLE]}
    assert BENIGN not in str(result)


@pytest.mark.parametrize("warning", ["Fixture synthetic warning", {"message": "Fixture synthetic warning"}])
def test_unknown_warning_fails_closed_without_echoing_raw_content(warning):
    # The client wire contract rejects object warnings; direct classifier calls
    # conservatively classify any unsupported in-memory value as UNKNOWN.
    page = PaginationPageMetadata(3, (warning,))
    with pytest.raises(SourceWarningError) as error:
        classify_page_warnings("flows", "smart_money", page)
    assert UNKNOWN in str(error.value)
    assert "Fixture synthetic warning" not in str(error.value)


def test_multiple_warnings_are_counted_and_unknown_is_not_masked():
    page = PaginationPageMetadata(2, (BENIGN, "unrelated synthetic warning"))
    with pytest.raises(SourceWarningError) as error:
        classify_page_warnings("flows", "smart_money", page)
    assert error.value.warning_count == 2
    assert UNKNOWN in error.value.categories


def test_benign_semantics_are_not_allowed_for_unverified_endpoint_or_label():
    with pytest.raises(SourceWarningError):
        classify_page_warnings("dex-trades", None, PaginationPageMetadata(1, (BENIGN,)))
