"""Chain-aware token identity comparison rules."""

import re

EVM_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")


def canonical_chain_address(chain: str, address: str) -> str:
    """Return the persistence representation for a chain-specific address."""
    if not isinstance(address, str) or not address:
        raise ValueError("address must be a non-empty string")
    if chain.casefold() == "avalanche":
        if not EVM_ADDRESS_PATTERN.fullmatch(address):
            raise ValueError("avalanche address must be a 0x-prefixed 40-hex address")
        return address.lower()
    return address


def canonical_flow_scope(flow_label: str) -> str:
    """Normalize flow scope whitespace without changing meaningful case."""
    if not isinstance(flow_label, str):
        raise ValueError("flow scope must be a string")
    value = flow_label.strip()
    if not value:
        raise ValueError("flow scope must be non-empty")
    return value


def token_identity_matches(chain: str, expected: str, actual: str) -> bool:
    """Compare token identities without applying EVM rules to Base58 chains."""
    if chain.casefold() == "avalanche":
        return bool(EVM_ADDRESS_PATTERN.fullmatch(expected)) and bool(EVM_ADDRESS_PATTERN.fullmatch(actual)) and expected.casefold() == actual.casefold()
    return expected == actual
