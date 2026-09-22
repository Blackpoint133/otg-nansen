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


class ResponseContractError(NansenError):
    """Raised when a response does not match the endpoint contract."""


class NansenTransportError(NansenError):
    """Raised when a bounded request fails at the transport layer."""


class PaginationLimitReached(NansenError):
    """Raised when a paginated response remains incomplete at the page limit."""

    def __init__(self, endpoint: str, pages_fetched: int, records_collected: int):
        super().__init__(
            f"pagination limit reached: endpoint={endpoint} "
            f"pages_fetched={pages_fetched} records_collected={records_collected}"
        )
        self.endpoint = endpoint
        self.pages_fetched = pages_fetched
        self.records_collected = records_collected


class NormalizationError(NansenError):
    """Raised when a required normalized field is malformed or missing."""


class IncompleteSourceWindow(NansenError):
    """Raised when a historical flow window contains incomplete records."""


class IngestionWindowError(NansenError):
    """Raised when a requested ingestion window is invalid or unsafe."""
