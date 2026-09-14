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
        """natural-language search over urls across Semble by meaning (vector
        search). `query` must be non-empty. `identifier` scopes results to one
        user's library (to read a whole library use cards list_by_user instead);
        `url_type` filters by kind of content. each result carries
        `url_library_count` (how many libraries saved it) and `url_in_library`
        (whether the caller saved it): a result with `url_library_count` of 0 is
        known to Semble only through connections, nobody has saved it, so keep
        that field when recommending things people actually saved.
        """
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
        """urls across Semble semantically similar to a given url (vector
        similarity). `threshold` between 0 and 1 drops weak matches. results
        carry `url_library_count` and `url_in_library` like semantic search.
        """
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
        """find Semble user accounts by a fragment of handle or display name (`q`).
        only for discovering accounts you do not already know: with a known
        handle or DID, call actors get_profile or cards list_by_user directly
        instead.
        """
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
        """natural-language search over urls across Semble by meaning (vector
        search). `query` must be non-empty. `identifier` scopes results to one
        user's library (to read a whole library use cards list_by_user instead);
        `url_type` filters by kind of content. each result carries
        `url_library_count` (how many libraries saved it) and `url_in_library`
        (whether the caller saved it): a result with `url_library_count` of 0 is
        known to Semble only through connections, nobody has saved it, so keep
        that field when recommending things people actually saved.
        """
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
        """urls across Semble semantically similar to a given url (vector
        similarity). `threshold` between 0 and 1 drops weak matches. results
        carry `url_library_count` and `url_in_library` like semantic search.
        """
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
        """find Semble user accounts by a fragment of handle or display name (`q`).
        only for discovering accounts you do not already know: with a known
        handle or DID, call actors get_profile or cards list_by_user directly
        instead.
        """
        params = drop_none(term=term, q=q, limit=limit, cursor=cursor)
        return await self._client.get(
            "network.cosmik.search.getAccounts", params, cast_to=Page[User]
        )
