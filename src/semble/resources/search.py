"""network.cosmik.search.* — semantic and similarity search."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import Page, SortOrder, URLType, URLView, User


class Search(SyncResource):
    def semantic(
        self,
        query: str,
        *,
        threshold: float | None = None,
        url_type: URLType | None = None,
        identifier: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[URLView]:
        params = drop_none(
            query=query,
            threshold=threshold,
            urlType=url_type,
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.search.semantic", params, cast_to=Page[URLView]
        )

    def get_similar_urls(
        self,
        url: str,
        *,
        threshold: float | None = None,
        url_type: URLType | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[URLView]:
        params = drop_none(
            url=url,
            threshold=threshold,
            urlType=url_type,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.search.getSimilarUrls", params, cast_to=Page[URLView]
        )

    def get_accounts(
        self,
        *,
        term: str | None = None,
        q: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[User]:
        params = drop_none(term=term, q=q, limit=limit, cursor=cursor)
        return self._client.get(
            "network.cosmik.search.getAccounts", params, cast_to=Page[User]
        )


class AsyncSearch(AsyncResource):
    async def semantic(
        self,
        query: str,
        *,
        threshold: float | None = None,
        url_type: URLType | None = None,
        identifier: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[URLView]:
        params = drop_none(
            query=query,
            threshold=threshold,
            urlType=url_type,
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.search.semantic", params, cast_to=Page[URLView]
        )

    async def get_similar_urls(
        self,
        url: str,
        *,
        threshold: float | None = None,
        url_type: URLType | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[URLView]:
        params = drop_none(
            url=url,
            threshold=threshold,
            urlType=url_type,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.search.getSimilarUrls", params, cast_to=Page[URLView]
        )

    async def get_accounts(
        self,
        *,
        term: str | None = None,
        q: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page[User]:
        params = drop_none(term=term, q=q, limit=limit, cursor=cursor)
        return await self._client.get(
            "network.cosmik.search.getAccounts", params, cast_to=Page[User]
        )
