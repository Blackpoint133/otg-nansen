"""Tests for chain-aware token identity semantics."""

from otg_nansen.identity import token_identity_matches
from otg_nansen.normalize import normalize_token_information
from otg_nansen.errors import NormalizationError


def test_avalanche_evm_identity_is_case_insensitive():
    expected = "0x00000000000000000000000000000000000000Aa"
    actual = "0x00000000000000000000000000000000000000aA"
    assert token_identity_matches("avalanche", expected, actual)


def test_avalanche_different_address_does_not_match():
    assert not token_identity_matches(
        "avalanche",
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
    )


def test_solana_identity_is_exact_and_case_sensitive():
    address = "3jUf2RTyXp867piSB2dt8uUcNiLDW58asjGtXkRAkBbe"
    assert token_identity_matches("solana", address, address)
    assert not token_identity_matches("solana", address, address.swapcase())


def test_unknown_chain_uses_exact_comparison():
    assert token_identity_matches("unknown-chain", "TokenABC", "TokenABC")
    assert not token_identity_matches("unknown-chain", "TokenABC", "tokenabc")


def test_solana_normalizer_rejects_case_only_identity_mismatch():
    response = {
        "data": {
            "name": "GUN",
            "symbol": "GUN",
            "contract_address": "3jUf2RTyXp867piSB2dt8uUcNiLDW58asjGtXkRAkBe",
            "token_details": {},
            "spot_metrics": {},
        }
    }
    from pytest import raises
    with raises(NormalizationError):
        normalize_token_information(
            response,
            chain="solana",
            token_address="3jUf2RTyXp867piSB2dt8uUcNiLDW58asjGtXkRAkBbe",
        )
