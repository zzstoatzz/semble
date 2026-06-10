"""network.cosmik.graph.* — following users and collections."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import Collection, CountResponse, IDResponse, Page, TargetType, User


class Graph(SyncResource):
    def follow(self, target_id: str, target_type: TargetType) -> IDResponse:
        return self._client.post(
            "network.cosmik.graph.follow",
            {"targetId": target_id, "targetType": target_type},
            cast_to=IDResponse,
        )

    def unfollow(self, target_id: str, target_type: TargetType) -> IDResponse:
        return self._client.post(
            "network.cosmik.graph.unfollow",
            {"targetId": target_id, "targetType": target_type},
            cast_to=IDResponse,
        )

    def get_following(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.graph.getFollowing", params, cast_to=Page[User]
        )

    def get_followers(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.graph.getFollowers", params, cast_to=Page[User]
        )

    def get_following_collections(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[Collection]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return self._client.get(
            "network.cosmik.graph.getFollowingCollections",
            params,
            cast_to=Page[Collection],
        )

    def get_following_count(self, identifier: str) -> CountResponse:
        return self._client.get(
            "network.cosmik.graph.getFollowingCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )

    def get_followers_count(self, identifier: str) -> CountResponse:
        return self._client.get(
            "network.cosmik.graph.getFollowersCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )

    def get_following_collections_count(self, identifier: str) -> CountResponse:
        return self._client.get(
            "network.cosmik.graph.getFollowingCollectionsCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )


class AsyncGraph(AsyncResource):
    async def follow(self, target_id: str, target_type: TargetType) -> IDResponse:
        return await self._client.post(
            "network.cosmik.graph.follow",
            {"targetId": target_id, "targetType": target_type},
            cast_to=IDResponse,
        )

    async def unfollow(self, target_id: str, target_type: TargetType) -> IDResponse:
        return await self._client.post(
            "network.cosmik.graph.unfollow",
            {"targetId": target_id, "targetType": target_type},
            cast_to=IDResponse,
        )

    async def get_following(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.graph.getFollowing", params, cast_to=Page[User]
        )

    async def get_followers(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[User]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.graph.getFollowers", params, cast_to=Page[User]
        )

    async def get_following_collections(
        self,
        identifier: str,
        *,
        page: int | None = None,
        limit: int | None = None,
    ) -> Page[Collection]:
        params = drop_none(identifier=identifier, page=page, limit=limit)
        return await self._client.get(
            "network.cosmik.graph.getFollowingCollections",
            params,
            cast_to=Page[Collection],
        )

    async def get_following_count(self, identifier: str) -> CountResponse:
        return await self._client.get(
            "network.cosmik.graph.getFollowingCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )

    async def get_followers_count(self, identifier: str) -> CountResponse:
        return await self._client.get(
            "network.cosmik.graph.getFollowersCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )

    async def get_following_collections_count(self, identifier: str) -> CountResponse:
        return await self._client.get(
            "network.cosmik.graph.getFollowingCollectionsCount",
            {"identifier": identifier},
            cast_to=CountResponse,
        )
