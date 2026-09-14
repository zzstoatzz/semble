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
        """create a collection for the authenticated user. OPEN lets others
        contribute cards; CLOSED means only the owner adds them. neither is
        private.
        """
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
        """a collection with its cards, paginated, by collection id (uuid)."""
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
        """a collection with its cards, looked up by the owner's handle and the
        record key from its at:// uri.
        """
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
        """rename a collection, change its description, or switch its access type
        between OPEN and CLOSED.
        """
        body = drop_none(
            collectionId=collection_id,
            name=name,
            description=description,
            accessType=access_type,
        )
        self._client.post("network.cosmik.collection.update", body)

    def delete(self, collection_id: str) -> None:
        """permanently delete a collection owned by the authenticated user. its
        cards stay in the library.
        """
        self._client.post(
            "network.cosmik.collection.delete", {"collectionId": collection_id}
        )

    def _resolve_id(self, collection_id: str) -> str:
        if not collection_id.startswith("at://"):
            return collection_id
        _, _, rest = collection_id.partition("at://")
        handle, _, record_key = rest.replace(
            "/network.cosmik.collection/", "/"
        ).partition("/")
        resolved = self.get_by_at_uri(handle, record_key, limit=1).id
        if resolved is None:
            raise ValueError(f"could not resolve collection at-uri: {collection_id}")
        return resolved

    def add_card(self, collection_id: str, card_id: str) -> None:
        """add a card to a collection. accepts a collection uuid or at-uri."""
        self._client.post(
            "network.cosmik.card.updateUrlAssociations",
            {"cardId": card_id, "addToCollections": [self._resolve_id(collection_id)]},
        )

    def remove_card(self, collection_id: str, card_id: str) -> None:
        """remove a card from a collection. accepts a collection uuid or at-uri."""
        self._client.post(
            "network.cosmik.card.updateUrlAssociations",
            {
                "cardId": card_id,
                "removeFromCollections": [self._resolve_id(collection_id)],
            },
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
        """the authenticated user's own collections, paginated. `search_text`
        filters by name or description.
        """
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
        """collections owned by a user, by handle or DID, paginated. `search_text`
        filters by name or description.
        """
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
        """open collections a user has contributed cards to, by handle or DID,
        paginated.
        """
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
        """collections across Semble that contain a url, paginated."""
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
        """full-text search over collection names and descriptions across Semble,
        optionally scoped to one user (`identifier`) or access type.
        """
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
        """users who follow a collection, paginated."""
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.collection.getFollowers", params, cast_to=Page[User]
        )

    def get_follower_count(self, collection_id: str) -> CountResponse:
        """how many users follow a collection."""
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
        """users who have added cards to a collection, paginated."""
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
        """create a collection for the authenticated user. OPEN lets others
        contribute cards; CLOSED means only the owner adds them. neither is
        private.
        """
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
        """a collection with its cards, paginated, by collection id (uuid)."""
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
        """a collection with its cards, looked up by the owner's handle and the
        record key from its at:// uri.
        """
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
        """rename a collection, change its description, or switch its access type
        between OPEN and CLOSED.
        """
        body = drop_none(
            collectionId=collection_id,
            name=name,
            description=description,
            accessType=access_type,
        )
        await self._client.post("network.cosmik.collection.update", body)

    async def delete(self, collection_id: str) -> None:
        """permanently delete a collection owned by the authenticated user. its
        cards stay in the library.
        """
        await self._client.post(
            "network.cosmik.collection.delete", {"collectionId": collection_id}
        )

    async def _resolve_id(self, collection_id: str) -> str:
        if not collection_id.startswith("at://"):
            return collection_id
        _, _, rest = collection_id.partition("at://")
        handle, _, record_key = rest.replace(
            "/network.cosmik.collection/", "/"
        ).partition("/")
        resolved = (await self.get_by_at_uri(handle, record_key, limit=1)).id
        if resolved is None:
            raise ValueError(f"could not resolve collection at-uri: {collection_id}")
        return resolved

    async def add_card(self, collection_id: str, card_id: str) -> None:
        """add a card to a collection. accepts a collection uuid or at-uri."""
        await self._client.post(
            "network.cosmik.card.updateUrlAssociations",
            {
                "cardId": card_id,
                "addToCollections": [await self._resolve_id(collection_id)],
            },
        )

    async def remove_card(self, collection_id: str, card_id: str) -> None:
        """remove a card from a collection. accepts a collection uuid or at-uri."""
        await self._client.post(
            "network.cosmik.card.updateUrlAssociations",
            {
                "cardId": card_id,
                "removeFromCollections": [await self._resolve_id(collection_id)],
            },
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
        """the authenticated user's own collections, paginated. `search_text`
        filters by name or description.
        """
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
        """collections owned by a user, by handle or DID, paginated. `search_text`
        filters by name or description.
        """
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
        """open collections a user has contributed cards to, by handle or DID,
        paginated.
        """
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
        """collections across Semble that contain a url, paginated."""
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
        """full-text search over collection names and descriptions across Semble,
        optionally scoped to one user (`identifier`) or access type.
        """
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
        """users who follow a collection, paginated."""
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.collection.getFollowers", params, cast_to=Page[User]
        )

    async def get_follower_count(self, collection_id: str) -> CountResponse:
        """how many users follow a collection."""
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
        """users who have added cards to a collection, paginated."""
        params = drop_none(collectionId=collection_id, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.collection.getContributors", params, cast_to=Page[User]
        )
