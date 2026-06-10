"""network.cosmik.actor.* — user profiles."""

from semble._utils import drop_none
from semble.resources._base import AsyncResource, SyncResource
from semble.types import User


class Actors(SyncResource):
    def get_my_profile(self, *, include_stats: bool | None = None) -> User:
        params = drop_none(includeStats=include_stats)
        return self._client.get(
            "network.cosmik.actor.getMyProfile", params, cast_to=User
        )

    def get_profile(
        self, identifier: str, *, include_stats: bool | None = None
    ) -> User:
        params = drop_none(identifier=identifier, includeStats=include_stats)
        return self._client.get("network.cosmik.actor.getProfile", params, cast_to=User)


class AsyncActors(AsyncResource):
    async def get_my_profile(self, *, include_stats: bool | None = None) -> User:
        params = drop_none(includeStats=include_stats)
        return await self._client.get(
            "network.cosmik.actor.getMyProfile", params, cast_to=User
        )

    async def get_profile(
        self, identifier: str, *, include_stats: bool | None = None
    ) -> User:
        params = drop_none(identifier=identifier, includeStats=include_stats)
        return await self._client.get(
            "network.cosmik.actor.getProfile", params, cast_to=User
        )
