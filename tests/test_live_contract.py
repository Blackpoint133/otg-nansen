"""Opt-in live checks; default test runs never spend API credits."""

import os

import pytest

from otg_nansen.client import NansenClient
from otg_nansen.config import NansenConfig, TOKEN_IDENTITIES


pytestmark = pytest.mark.live


@pytest.mark.skipif(os.getenv("NANSEN_RUN_LIVE_TESTS") != "1", reason="set NANSEN_RUN_LIVE_TESTS=1 to opt in")
def test_live_avalanche_contract():
    client = NansenClient(NansenConfig.from_env())
    result = client.token_information("avalanche", TOKEN_IDENTITIES["avalanche"], timeframe="1d")
    assert isinstance(result, dict)
    assert client.requests_attempted == 1
