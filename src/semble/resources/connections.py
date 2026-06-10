"""network.cosmik.connection.* — typed links between urls."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import ConnectionType, ConnectionView, IDResponse, Page, SortOrder


class Connections(SyncResource):
    def create(
        self,
        *,
        source_type: str | None = None,
        source_value: str | None = None,
        target_type: str | None = None,
        target_value: str | None = None,
        connection_type: ConnectionType | None = None,
        note: str | None = None,
    ) -> IDResponse:
        body = drop_none(
            sourceType=source_type,
            sourceValue=source_value,
            targetType=target_type,
            targetValue=target_value,
            connectionType=connection_type,
            note=note,
        )
        return self._client.post(
            "network.cosmik.connection.create", body, cast_to=IDResponse
        )

    def update(
        self,
        connection_id: str,
        *,
        connection_type: ConnectionType | None = None,
        note: str | None = None,
        remove_note: bool | None = None,
        swap: bool | None = None,
    ) -> IDResponse:
        body = drop_none(
            connectionId=connection_id,
            connectionType=connection_type,
            note=note,
            removeNote=remove_note,
            swap=swap,
        )
        return self._client.post(
            "network.cosmik.connection.update", body, cast_to=IDResponse
        )

    def delete(self, connection_id: str) -> IDResponse:
        return self._client.post(
            "network.cosmik.connection.delete",
            {"connectionId": connection_id},
            cast_to=IDResponse,
        )

    def get_for_url(
        self,
        url: str,
        *,
        direction: str | None = None,
        connection_types: list[ConnectionType] | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[ConnectionView]:
        params = drop_none(
            url=url,
            direction=direction,
            connectionTypes=connection_types,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.connection.getForUrl", params, cast_to=Page[ConnectionView]
        )

    def list_by_user(
        self,
        identifier: str,
        *,
        connection_types: list[ConnectionType] | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[ConnectionView]:
        params = drop_none(
            identifier=identifier,
            connectionTypes=connection_types,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.connection.listByUser", params, cast_to=Page[ConnectionView]
        )


class AsyncConnections(AsyncResource):
    async def create(
        self,
        *,
        source_type: str | None = None,
        source_value: str | None = None,
        target_type: str | None = None,
        target_value: str | None = None,
        connection_type: ConnectionType | None = None,
        note: str | None = None,
    ) -> IDResponse:
        body = drop_none(
            sourceType=source_type,
            sourceValue=source_value,
            targetType=target_type,
            targetValue=target_value,
            connectionType=connection_type,
            note=note,
        )
        return await self._client.post(
            "network.cosmik.connection.create", body, cast_to=IDResponse
        )

    async def update(
        self,
        connection_id: str,
        *,
        connection_type: ConnectionType | None = None,
        note: str | None = None,
        remove_note: bool | None = None,
        swap: bool | None = None,
    ) -> IDResponse:
        body = drop_none(
            connectionId=connection_id,
            connectionType=connection_type,
            note=note,
            removeNote=remove_note,
            swap=swap,
        )
        return await self._client.post(
            "network.cosmik.connection.update", body, cast_to=IDResponse
        )

    async def delete(self, connection_id: str) -> IDResponse:
        return await self._client.post(
            "network.cosmik.connection.delete",
            {"connectionId": connection_id},
            cast_to=IDResponse,
        )

    async def get_for_url(
        self,
        url: str,
        *,
        direction: str | None = None,
        connection_types: list[ConnectionType] | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[ConnectionView]:
        params = drop_none(
            url=url,
            direction=direction,
            connectionTypes=connection_types,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.connection.getForUrl", params, cast_to=Page[ConnectionView]
        )

    async def list_by_user(
        self,
        identifier: str,
        *,
        connection_types: list[ConnectionType] | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[ConnectionView]:
        params = drop_none(
            identifier=identifier,
            connectionTypes=connection_types,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.connection.listByUser", params, cast_to=Page[ConnectionView]
        )
