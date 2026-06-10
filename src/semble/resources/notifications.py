"""network.cosmik.notification.* — your notification inbox."""

# Sequence (not list) in mark_read: the `list` methods shadow the builtin
# inside these class bodies
from collections.abc import Sequence

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import CountResponse, IDResponse, Notification, Page, SortOrder


class Notifications(SyncResource):
    def list(
        self,
        *,
        unread_only: bool | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Notification]:
        params = drop_none(
            unreadOnly=unread_only,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.notification.list", params, cast_to=Page[Notification]
        )

    def get_unread_count(self) -> CountResponse:
        return self._client.get(
            "network.cosmik.notification.getUnreadCount", cast_to=CountResponse
        )

    def mark_read(self, notification_ids: Sequence[str]) -> IDResponse:
        return self._client.post(
            "network.cosmik.notification.markRead",
            {"notificationIds": [*notification_ids]},
            cast_to=IDResponse,
        )

    def mark_all_read(self) -> IDResponse:
        return self._client.post(
            "network.cosmik.notification.markAllRead", {}, cast_to=IDResponse
        )


class AsyncNotifications(AsyncResource):
    async def list(
        self,
        *,
        unread_only: bool | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Notification]:
        params = drop_none(
            unreadOnly=unread_only,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.notification.list", params, cast_to=Page[Notification]
        )

    async def get_unread_count(self) -> CountResponse:
        return await self._client.get(
            "network.cosmik.notification.getUnreadCount", cast_to=CountResponse
        )

    async def mark_read(self, notification_ids: Sequence[str]) -> IDResponse:
        return await self._client.post(
            "network.cosmik.notification.markRead",
            {"notificationIds": [*notification_ids]},
            cast_to=IDResponse,
        )

    async def mark_all_read(self) -> IDResponse:
        return await self._client.post(
            "network.cosmik.notification.markAllRead", {}, cast_to=IDResponse
        )
