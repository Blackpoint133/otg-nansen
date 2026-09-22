"""Non-secret client configuration and verified public token identities."""

from dataclasses import dataclass
import math
import os
from typing import Optional

from .errors import ConfigurationError

DEFAULT_BASE_URL = "https://api.nansen.ai"
TOKEN_IDENTITIES = {
    "avalanche": "0x26deBD39D5eD069770406FCa10A0E4f8d2c743eB",
    "solana": "3jUf2RTyXp867piSB2dt8uUcNiLDW58asjGtXkRAkBbe",
}


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if parsed < 1:
        raise ConfigurationError(f"{name} must be positive")
    return parsed


def _nonnegative_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if parsed < 0:
        raise ConfigurationError(f"{name} must not be negative")
    return parsed


def _positive_float(value: str, name: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ConfigurationError(f"{name} must be finite and greater than zero")
    return parsed


def _optional_nonnegative_float(value: Optional[str], name: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a number") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise ConfigurationError(f"{name} must be finite and nonnegative")
    return parsed


@dataclass(frozen=True)
class NansenConfig:
    """Bounded settings for one client run."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 20.0
    max_retries: int = 2
    max_calls: int = 20
    rate_pacing_seconds: Optional[float] = None
    page_size: int = 2
    max_pages: int = 10

    @classmethod
    def from_env(cls) -> "NansenConfig":
        api_key = os.getenv("NANSEN_API_KEY")
        if not api_key:
            raise ConfigurationError("NANSEN_API_KEY is required")
        return cls(
            api_key=api_key,
            base_url=os.getenv("NANSEN_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            timeout_seconds=_positive_float(os.getenv("NANSEN_TIMEOUT_SECONDS", "20"), "NANSEN_TIMEOUT_SECONDS"),
            max_retries=_nonnegative_int(os.getenv("NANSEN_MAX_RETRIES", "2"), "NANSEN_MAX_RETRIES"),
            max_calls=_positive_int(os.getenv("NANSEN_MAX_CALLS", "20"), "NANSEN_MAX_CALLS"),
            rate_pacing_seconds=_optional_nonnegative_float(
                os.getenv("NANSEN_RATE_PACING_SECONDS"), "NANSEN_RATE_PACING_SECONDS"
            ),
            page_size=_positive_int(os.getenv("NANSEN_PAGE_SIZE", "2"), "NANSEN_PAGE_SIZE"),
            max_pages=_positive_int(os.getenv("NANSEN_MAX_PAGES", "10"), "NANSEN_MAX_PAGES"),
        )
