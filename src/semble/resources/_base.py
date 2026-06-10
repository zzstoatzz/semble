from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from semble._client import AsyncSemble, Semble


class SyncResource:
    def __init__(self, client: "Semble") -> None:
        self._client = client


class AsyncResource:
    def __init__(self, client: "AsyncSemble") -> None:
        self._client = client
