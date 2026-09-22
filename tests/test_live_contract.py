"""Opt-in live checks; default test runs never spend API credits."""

import os

import pytest

from otg_nansen.client import NansenClient
from otg_nansen.config import NansenConfig, TOKEN_IDENTITIES


pytestmark = pytest.mark.live


@pytest.mark.skipif(os.getenv("NANSEN_RUN_LIVE_TESTS") != "1", reason="set NANSEN_RUN_LIVE_TESTS=1 to opt in")
def test_live_avalanche_contract():
    base = NansenConfig.from_env()
    config = base.__class__(api_key=base.api_key, base_url=base.base_url, timeout_seconds=base.timeout_seconds, max_retries=0, max_calls=3, page_size=2, max_pages=1)
    client = NansenClient(config)
    window = {"from": "2026-09-20T00:00:00Z", "to": "2026-09-22T23:59:59Z"}
    token = client.token_information("avalanche", TOKEN_IDENTITIES["avalanche"], timeframe="1d")
    flows = client.flows("avalanche", TOKEN_IDENTITIES["avalanche"], date=window, label="smart_money", pagination={"page": 1, "per_page": 2})
    trades = client.dex_trades("avalanche", TOKEN_IDENTITIES["avalanche"], date=window, pagination={"page": 1, "per_page": 2})
    assert isinstance(token.get("data"), dict)
    assert isinstance(flows.get("data"), list)
    assert isinstance(trades.get("data"), list)
    assert client.requests_attempted == 3
