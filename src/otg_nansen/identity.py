"""Chain-aware token identity comparison rules."""

import re

EVM_ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")


def token_identity_matches(chain: str, expected: str, actual: str) -> bool:
    """Compare token identities without applying EVM rules to Base58 chains."""
    if chain.casefold() == "avalanche":
        return bool(EVM_ADDRESS_PATTERN.fullmatch(expected)) and bool(EVM_ADDRESS_PATTERN.fullmatch(actual)) and expected.casefold() == actual.casefold()
    return expected == actual
