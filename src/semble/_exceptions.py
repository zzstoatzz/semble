import httpx2


class SembleError(Exception):
    """base for all errors raised by this library."""


class APIStatusError(SembleError):
    """a non-2xx response from the semble api."""

    def __init__(self, message: str, *, response: httpx2.Response) -> None:
        super().__init__(message)
        self.message = message
        self.response = response
        self.status_code = response.status_code


class AuthenticationError(APIStatusError):
    """401 — missing or invalid api key."""


class PermissionDeniedError(APIStatusError):
    """403 — authenticated but not allowed."""


class NotFoundError(APIStatusError):
    """404 — no such resource."""


class RateLimitError(APIStatusError):
    """429 — slow down."""


class ServerError(APIStatusError):
    """5xx — something broke on semble's end."""


_STATUS_ERRORS: dict[int, type[APIStatusError]] = {
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def status_error(response: httpx2.Response) -> APIStatusError:
    message = ""
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        message = data.get("message") or data.get("error") or ""
    if not message:
        message = response.text.strip() or f"HTTP {response.status_code}"

    cls = _STATUS_ERRORS.get(response.status_code)
    if cls is None:
        cls = ServerError if response.status_code >= 500 else APIStatusError
    return cls(message, response=response)
