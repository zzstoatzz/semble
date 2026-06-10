"""network.cosmik.feed.* — global and following activity feeds."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import Activity, Page, SortOrder, URLType


class Feeds(SyncResource):
    def get_global(
        self,
        *,
        url_type: URLType | None = None,
        source: str | None = None,
        activity_types: list[str] | None = None,
        include_known_bots: bool | None = None,
        before_activity_id: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Activity]:
        params = drop_none(
            urlType=url_type,
            source=source,
            activityTypes=activity_types,
            includeKnownBots=include_known_bots,
            beforeActivityId=before_activity_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.feed.getGlobal", params, cast_to=Page[Activity]
        )

    def get_following(
        self,
        *,
        url_type: URLType | None = None,
        source: str | None = None,
        activity_types: list[str] | None = None,
        include_known_bots: bool | None = None,
        before_activity_id: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Activity]:
        params = drop_none(
            urlType=url_type,
            source=source,
            activityTypes=activity_types,
            includeKnownBots=include_known_bots,
            beforeActivityId=before_activity_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return self._client.get(
            "network.cosmik.feed.getFollowing", params, cast_to=Page[Activity]
        )


class AsyncFeeds(AsyncResource):
    async def get_global(
        self,
        *,
        url_type: URLType | None = None,
        source: str | None = None,
        activity_types: list[str] | None = None,
        include_known_bots: bool | None = None,
        before_activity_id: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Activity]:
        params = drop_none(
            urlType=url_type,
            source=source,
            activityTypes=activity_types,
            includeKnownBots=include_known_bots,
            beforeActivityId=before_activity_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.feed.getGlobal", params, cast_to=Page[Activity]
        )

    async def get_following(
        self,
        *,
        url_type: URLType | None = None,
        source: str | None = None,
        activity_types: list[str] | None = None,
        include_known_bots: bool | None = None,
        before_activity_id: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        sort_by: str | None = None,
        sort_order: SortOrder | None = None,
    ) -> Page[Activity]:
        params = drop_none(
            urlType=url_type,
            source=source,
            activityTypes=activity_types,
            includeKnownBots=include_known_bots,
            beforeActivityId=before_activity_id,
            page=page,
            limit=limit,
            sortBy=sort_by,
            sortOrder=sort_order,
        )
        return await self._client.get(
            "network.cosmik.feed.getFollowing", params, cast_to=Page[Activity]
        )
