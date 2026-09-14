import httpx2 as httpx


class SembleError(Exception):
    """base for all errors raised by this library."""


class APIStatusError(SembleError):
    """a non-2xx response from the semble api."""

    def __init__(self, message: str, *, response: httpx.Response) -> None:
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


def _field_errors(errors: object) -> str:
    """flatten semble's zod-style `errors` payload into `field: reason` pairs."""
    if not isinstance(errors, dict):
        return ""
    payload: dict[str, object] = {str(k): v for k, v in errors.items()}
    parts: list[str] = []
    field_errors = payload.get("fieldErrors")
    if isinstance(field_errors, dict):
        for field, reasons in field_errors.items():
            if isinstance(reasons, list) and reasons:
                parts.append(f"{field}: {'; '.join(str(r) for r in reasons)}")
    form_errors = payload.get("formErrors")
    if isinstance(form_errors, list) and form_errors:
        parts.append("; ".join(str(r) for r in form_errors))
    return ", ".join(parts)


def status_error(response: httpx.Response) -> APIStatusError:
    message = ""
    try:
        data = response.json()
    except ValueError:
        data = None
    if isinstance(data, dict):
        message = data.get("message") or data.get("error") or ""
        details = _field_errors(data.get("errors"))
        if details:
            message = f"{message or 'Validation error'}: {details}"
    if not message:
        message = response.text.strip() or f"HTTP {response.status_code}"

    cls = _STATUS_ERRORS.get(response.status_code)
    if cls is None:
        cls = ServerError if response.status_code >= 500 else APIStatusError
    return cls(message, response=response)
