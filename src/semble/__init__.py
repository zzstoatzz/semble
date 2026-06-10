from importlib.metadata import PackageNotFoundError, version

from semble._client import AsyncSemble, Semble
from semble.settings import DEFAULT_BASE_URL, SembleSettings
from semble._exceptions import (
    APIStatusError,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SembleError,
    ServerError,
)

try:
    __version__ = version("semble-api")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "DEFAULT_BASE_URL",
    "APIStatusError",
    "AsyncSemble",
    "AuthenticationError",
    "NotFoundError",
    "PermissionDeniedError",
    "RateLimitError",
    "Semble",
    "SembleError",
    "SembleSettings",
    "ServerError",
    "__version__",
]
