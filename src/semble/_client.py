from types import TracebackType
from typing import Any

import httpx2
from pydantic import SecretStr

from semble._exceptions import status_error
from semble.resources.actors import Actors, AsyncActors
from semble.resources.cards import AsyncCards, Cards
from semble.resources.collections import AsyncCollections, Collections
from semble.resources.connections import AsyncConnections, Connections
from semble.resources.feeds import AsyncFeeds, Feeds
from semble.resources.graph import AsyncGraph, Graph
from semble.resources.notifications import AsyncNotifications, Notifications
from semble.resources.search import AsyncSearch, Search
from semble.settings import SembleSettings


class _BaseClient:
    def __init__(
        self,
        api_key: str | SecretStr | None,
        base_url: str | None,
        timeout: float | None,
    ) -> None:
        settings = SembleSettings()
        if api_key is None:
            self.api_key = settings.api_key
        elif isinstance(api_key, str):
            self.api_key = SecretStr(api_key) if api_key else None
        else:
            self.api_key = api_key
        self.base_url = (base_url or settings.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.timeout

    def _url(self, nsid: str) -> str:
        return f"{self.base_url}/{nsid}"

    def _headers(self) -> dict[str, str]:
        headers = {"accept": "application/json"}
        if self.api_key is not None:
            headers["x-api-key"] = self.api_key.get_secret_value()
        return headers

    @staticmethod
    def _parse(response: httpx2.Response, cast_to: Any) -> Any:
        if not response.is_success:
            raise status_error(response)
        if not response.content:
            return None
        data = response.json()
        if cast_to is None:
            return data
        return cast_to.model_validate(data)


class Semble(_BaseClient):
    """synchronous client for the semble api.

    configuration not passed explicitly comes from `SembleSettings`
    (`SEMBLE_*` environment variables, then a local `.env` file). create
    keys at https://semble.so/settings/api-keys.

    usable directly or as a context manager. `close()` only closes the
    underlying http client if this client created it — a borrowed
    `http_client` stays open and its lifecycle (including its timeout)
    remains the caller's.
    """

    def __init__(
        self,
        *,
        api_key: str | SecretStr | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        http_client: httpx2.Client | None = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout)
        self._owns_http = http_client is None
        self._http = http_client or httpx2.Client(timeout=self.timeout)

        self.actors = Actors(self)
        self.cards = Cards(self)
        self.collections = Collections(self)
        self.connections = Connections(self)
        self.feeds = Feeds(self)
        self.graph = Graph(self)
        self.notifications = Notifications(self)
        self.search = Search(self)

    def get(
        self,
        nsid: str,
        params: dict[str, Any] | None = None,
        *,
        cast_to: Any = None,
    ) -> Any:
        """GET an xrpc query by nsid. escape hatch for unwrapped endpoints."""
        response = self._http.get(
            self._url(nsid), params=params, headers=self._headers()
        )
        return self._parse(response, cast_to)

    def post(
        self,
        nsid: str,
        json: dict[str, Any] | None = None,
        *,
        cast_to: Any = None,
    ) -> Any:
        """POST an xrpc procedure by nsid. escape hatch for unwrapped endpoints."""
        response = self._http.post(self._url(nsid), json=json, headers=self._headers())
        return self._parse(response, cast_to)

    def close(self) -> None:
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> "Semble":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncSemble(_BaseClient):
    """asynchronous client for the semble api.

    configuration not passed explicitly comes from `SembleSettings`
    (`SEMBLE_*` environment variables, then a local `.env` file). create
    keys at https://semble.so/settings/api-keys.

    usable directly or as a context manager. `close()` only closes the
    underlying http client if this client created it — a borrowed
    `http_client` stays open and its lifecycle (including its timeout)
    remains the caller's.
    """

    def __init__(
        self,
        *,
        api_key: str | SecretStr | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        http_client: httpx2.AsyncClient | None = None,
    ) -> None:
        super().__init__(api_key, base_url, timeout)
        self._owns_http = http_client is None
        self._http = http_client or httpx2.AsyncClient(timeout=self.timeout)

        self.actors = AsyncActors(self)
        self.cards = AsyncCards(self)
        self.collections = AsyncCollections(self)
        self.connections = AsyncConnections(self)
        self.feeds = AsyncFeeds(self)
        self.graph = AsyncGraph(self)
        self.notifications = AsyncNotifications(self)
        self.search = AsyncSearch(self)

    async def get(
        self,
        nsid: str,
        params: dict[str, Any] | None = None,
        *,
        cast_to: Any = None,
    ) -> Any:
        """GET an xrpc query by nsid. escape hatch for unwrapped endpoints."""
        response = await self._http.get(
            self._url(nsid), params=params, headers=self._headers()
        )
        return self._parse(response, cast_to)

    async def post(
        self,
        nsid: str,
        json: dict[str, Any] | None = None,
        *,
        cast_to: Any = None,
    ) -> Any:
        """POST an xrpc procedure by nsid. escape hatch for unwrapped endpoints."""
        response = await self._http.post(
            self._url(nsid), json=json, headers=self._headers()
        )
        return self._parse(response, cast_to)

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "AsyncSemble":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
