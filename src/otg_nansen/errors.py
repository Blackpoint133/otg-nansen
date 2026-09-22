"""Public exception types for the Nansen client."""


class NansenError(Exception):
    """Base class for safe client errors."""


class ConfigurationError(NansenError):
    """Raised when required client configuration is missing or invalid."""


class RequestBudgetExceeded(NansenError):
    """Raised before a request would exceed the configured run budget."""


class NansenHTTPError(NansenError):
    """Raised for a non-successful HTTP response."""

    def __init__(self, endpoint: str, status_code: int, summary: str):
        super().__init__(f"Nansen request failed: endpoint={endpoint} status={status_code} response={summary}")
        self.endpoint = endpoint
        self.status_code = status_code


class ResponseDecodeError(NansenError):
    """Raised when a successful response is not valid JSON."""
