"""network.cosmik.card.* — urls and notes in libraries."""

from typing import Any

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import (
    AddURLResponse,
    LibraryEntry,
    NoteCard,
    Page,
    SortOrder,
    URLCard,
    URLMetadataResponse,
    URLType,
)


class Cards(SyncResource):
    def add_url(
        self,
        url: str,
        *,
        note: str | None = None,
        collection_ids: list[str] | None = None,
        via_card_id: str | None = None,
    ) -> AddURLResponse:
        """add a url to your library, optionally with a note and collections."""
        body = drop_none(
            url=url, note=note, collectionIds=collection_ids, viaCardId=via_card_id
        )
        return self._client.post(
            "network.cosmik.card.addUrl", body, cast_to=AddURLResponse
        )

    def update_url_associations(
        self,
        card_id: str,
        *,
        note: str | None = None,
        via_card_id: str | None = None,
        add_to_collections: list[str] | None = None,
        remove_from_collections: list[str] | None = None,
    ) -> None:
        body = drop_none(
            cardId=card_id,
            note=note,
            viaCardId=via_card_id,
            addToCollections=add_to_collections,
            removeFromCollections=remove_from_collections,
        )
        self._client.post("network.cosmik.card.updateUrlAssociations", body)

    def list_mine(
        self,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
        uncollected: bool | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
            uncollected=uncollected,
        )
        return self._client.get(
            "network.cosmik.card.listMine", params, cast_to=Page[URLCard]
        )

    def list_by_user(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
        uncollected: bool | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
            uncollected=uncollected,
        )
        return self._client.get(
            "network.cosmik.card.listByUser", params, cast_to=Page[URLCard]
        )

    def search(
        self,
        search_query: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            searchQuery=search_query,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return self._client.get(
            "network.cosmik.card.search", params, cast_to=Page[URLCard]
        )

    def get(self, card_id: str) -> URLCard:
        return self._client.get(
            "network.cosmik.card.get", {"cardId": card_id}, cast_to=URLCard
        )

    def get_url_metadata(
        self, url: str, *, include_stats: bool | None = None
    ) -> URLMetadataResponse:
        params = drop_none(url=url, includeStats=include_stats)
        return self._client.get(
            "network.cosmik.card.getUrlMetadata", params, cast_to=URLMetadataResponse
        )

    def get_library_status(self, url: str) -> dict[str, Any]:
        return self._client.get("network.cosmik.card.getLibraryStatus", {"url": url})

    def get_libraries_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[LibraryEntry]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return self._client.get(
            "network.cosmik.card.getLibrariesForUrl", params, cast_to=Page[LibraryEntry]
        )

    def get_note_cards_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[NoteCard]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return self._client.get(
            "network.cosmik.card.getNoteCardsForUrl", params, cast_to=Page[NoteCard]
        )

    def update_note(self, card_id: str, note: str) -> None:
        self._client.post(
            "network.cosmik.card.updateNote", {"cardId": card_id, "note": note}
        )

    def remove_from_library(self, card_id: str) -> None:
        self._client.post("network.cosmik.card.removeFromLibrary", {"cardId": card_id})


class AsyncCards(AsyncResource):
    async def add_url(
        self,
        url: str,
        *,
        note: str | None = None,
        collection_ids: list[str] | None = None,
        via_card_id: str | None = None,
    ) -> AddURLResponse:
        """add a url to your library, optionally with a note and collections."""
        body = drop_none(
            url=url, note=note, collectionIds=collection_ids, viaCardId=via_card_id
        )
        return await self._client.post(
            "network.cosmik.card.addUrl", body, cast_to=AddURLResponse
        )

    async def update_url_associations(
        self,
        card_id: str,
        *,
        note: str | None = None,
        via_card_id: str | None = None,
        add_to_collections: list[str] | None = None,
        remove_from_collections: list[str] | None = None,
    ) -> None:
        body = drop_none(
            cardId=card_id,
            note=note,
            viaCardId=via_card_id,
            addToCollections=add_to_collections,
            removeFromCollections=remove_from_collections,
        )
        await self._client.post("network.cosmik.card.updateUrlAssociations", body)

    async def list_mine(
        self,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
        uncollected: bool | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
            uncollected=uncollected,
        )
        return await self._client.get(
            "network.cosmik.card.listMine", params, cast_to=Page[URLCard]
        )

    async def list_by_user(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
        uncollected: bool | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            identifier=identifier,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
            uncollected=uncollected,
        )
        return await self._client.get(
            "network.cosmik.card.listByUser", params, cast_to=Page[URLCard]
        )

    async def search(
        self,
        search_query: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
        url_type: URLType | None = None,
    ) -> Page[URLCard]:
        params = drop_none(
            searchQuery=search_query,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
            urlType=url_type,
        )
        return await self._client.get(
            "network.cosmik.card.search", params, cast_to=Page[URLCard]
        )

    async def get(self, card_id: str) -> URLCard:
        return await self._client.get(
            "network.cosmik.card.get", {"cardId": card_id}, cast_to=URLCard
        )

    async def get_url_metadata(
        self, url: str, *, include_stats: bool | None = None
    ) -> URLMetadataResponse:
        params = drop_none(url=url, includeStats=include_stats)
        return await self._client.get(
            "network.cosmik.card.getUrlMetadata", params, cast_to=URLMetadataResponse
        )

    async def get_library_status(self, url: str) -> dict[str, Any]:
        return await self._client.get(
            "network.cosmik.card.getLibraryStatus", {"url": url}
        )

    async def get_libraries_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[LibraryEntry]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return await self._client.get(
            "network.cosmik.card.getLibrariesForUrl", params, cast_to=Page[LibraryEntry]
        )

    async def get_note_cards_for_url(
        self,
        url: str,
        *,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[NoteCard]:
        params = drop_none(
            url=url, page=page, limit=limit, sortBy=sort_by, sortOrder=sort_order
        )
        return await self._client.get(
            "network.cosmik.card.getNoteCardsForUrl", params, cast_to=Page[NoteCard]
        )

    async def update_note(self, card_id: str, note: str) -> None:
        await self._client.post(
            "network.cosmik.card.updateNote", {"cardId": card_id, "note": note}
        )

    async def remove_from_library(self, card_id: str) -> None:
        await self._client.post(
            "network.cosmik.card.removeFromLibrary", {"cardId": card_id}
        )
