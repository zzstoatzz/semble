"""network.cosmik.collection.* — named groups of cards."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import (
    AccessType,
    Collection,
    CollectionDetail,
    CountResponse,
    IDResponse,
    Page,
    SortOrder,
    URLType,
    User,
)


class Collections(SyncResource):
    def create(
        self,
        name: str,
        *,
        description: str | None = None,
        access_type: AccessType | None = None,
    ) -> IDResponse:
        body = drop_none(name=name, description=description, accessType=access_type)
        return self._client.post(
            "network.cosmik.collection.create", body, cast_to=IDResponse
        )

    def get(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> CollectionDetail:
        params = drop_none(
            collectionId=collection_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return self._client.get(
            "network.cosmik.collection.get", params, cast_to=CollectionDetail
        )

    def get_by_at_uri(
        self,
        handle: str,
        record_key: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> CollectionDetail:
        params = drop_none(
            handle=handle,
            recordKey=record_key,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return self._client.get(
            "network.cosmik.collection.getByAtUri", params, cast_to=CollectionDetail
        )

    def update(
        self,
        collection_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        access_type: AccessType | None = None,
    ) -> None:
        body = drop_none(
            collectionId=collection_id,
            name=name,
            description=description,
            accessType=access_type,
        )
        self._client.post("network.cosmik.collection.update", body)

    def delete(self, collection_id: str) -> None:
        self._client.post(
            "network.cosmik.collection.delete", {"collectionId": collection_id}
        )

    def list_mine(
        self,
        *,
        search_text: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            searchText=search_text,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.collection.listMine", params, cast_to=Page[Collection]
        )

    def list_by_user(
        self,
        identifier: str,
        *,
        search_text: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            identifier=identifier,
            searchText=search_text,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.collection.listByUser", params, cast_to=Page[Collection]
        )

    def list_contributed(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.collection.listContributed",
            params,
            cast_to=Page[Collection],
        )

    def get_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return self._client.get(
            "network.cosmik.collection.getForUrl", params, cast_to=Page[Collection]
        )

    def search(
        self,
        *,
        search_text: str | None = None,
        identifier: str | None = None,
        access_type: AccessType | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            searchText=search_text,
            identifier=identifier,
            accessType=access_type,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.collection.search", params, cast_to=Page[Collection]
        )

    def get_followers(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.collection.getFollowers", params, cast_to=Page[User]
        )

    def get_follower_count(self, collection_id: str) -> CountResponse:
        return self._client.get(
            "network.cosmik.collection.getFollowerCount",
            {"collectionId": collection_id},
            cast_to=CountResponse,
        )

    def get_contributors(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.collection.getContributors", params, cast_to=Page[User]
        )


class AsyncCollections(AsyncResource):
    async def create(
        self,
        name: str,
        *,
        description: str | None = None,
        access_type: AccessType | None = None,
    ) -> IDResponse:
        body = drop_none(name=name, description=description, accessType=access_type)
        return await self._client.post(
            "network.cosmik.collection.create", body, cast_to=IDResponse
        )

    async def get(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> CollectionDetail:
        params = drop_none(
            collectionId=collection_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return await self._client.get(
            "network.cosmik.collection.get", params, cast_to=CollectionDetail
        )

    async def get_by_at_uri(
        self,
        handle: str,
        record_key: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> CollectionDetail:
        params = drop_none(
            handle=handle,
            recordKey=record_key,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return await self._client.get(
            "network.cosmik.collection.getByAtUri", params, cast_to=CollectionDetail
        )

    async def update(
        self,
        collection_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        access_type: AccessType | None = None,
    ) -> None:
        body = drop_none(
            collectionId=collection_id,
            name=name,
            description=description,
            accessType=access_type,
        )
        await self._client.post("network.cosmik.collection.update", body)

    async def delete(self, collection_id: str) -> None:
        await self._client.post(
            "network.cosmik.collection.delete", {"collectionId": collection_id}
        )

    async def list_mine(
        self,
        *,
        search_text: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            searchText=search_text,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.collection.listMine", params, cast_to=Page[Collection]
        )

    async def list_by_user(
        self,
        identifier: str,
        *,
        search_text: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            identifier=identifier,
            searchText=search_text,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.collection.listByUser", params, cast_to=Page[Collection]
        )

    async def list_contributed(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.collection.listContributed",
            params,
            cast_to=Page[Collection],
        )

    async def get_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return await self._client.get(
            "network.cosmik.collection.getForUrl", params, cast_to=Page[Collection]
        )

    async def search(
        self,
        *,
        search_text: str | None = None,
        identifier: str | None = None,
        access_type: AccessType | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Collection]:
        params = drop_none(
            searchText=search_text,
            identifier=identifier,
            accessType=access_type,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.collection.search", params, cast_to=Page[Collection]
        )

    async def get_followers(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.collection.getFollowers", params, cast_to=Page[User]
        )

    async def get_follower_count(self, collection_id: str) -> CountResponse:
        return await self._client.get(
            "network.cosmik.collection.getFollowerCount",
            {"collectionId": collection_id},
            cast_to=CountResponse,
        )

    async def get_contributors(
        self,
        collection_id: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.collection.getContributors", params, cast_to=Page[User]
        )
