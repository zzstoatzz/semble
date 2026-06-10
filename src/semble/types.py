"""response models and shared types for the semble api.

field names are snake_case in python and map to the api's camelCase via
pydantic aliases. enum-ish request parameters are typed as `Literal` aliases;
the same fields on response models are plain `str` so new server-side values
never break parsing.
"""

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel

URLType = Literal[
    "article",
    "link",
    "book",
    "research",
    "audio",
    "video",
    "social",
    "event",
    "software",
]

AccessType = Literal["OPEN", "CLOSED"]

TargetType = Literal["USER", "COLLECTION"]

ConnectionType = Literal[
    "SUPPORTS",
    "OPPOSES",
    "ADDRESSES",
    "HELPFUL",
    "LEADS_TO",
    "RELATED",
    "SUPPLEMENT",
    "EXPLAINER",
]

SortOrder = Literal["asc", "desc"]


class Model(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
    )


class Pagination(Model):
    current_page: int | None = None
    total_pages: int | None = None
    total_count: int | None = None
    has_more: bool | None = None
    limit: int | None = None
    next_cursor: str | None = None


class User(Model):
    id: str | None = None
    name: str | None = None
    handle: str | None = None
    avatar_url: str | None = None
    banner_url: str | None = None
    description: str | None = None
    is_following: bool | None = None
    follows_you: bool | None = None
    follower_count: int | None = None
    following_count: int | None = None
    followed_collections_count: int | None = None
    url_card_count: int | None = None
    collection_count: int | None = None
    connection_count: int | None = None
    connections_by_type: dict[str, int] | None = None
    labels: list[Any] | None = None


class URLMetadata(Model):
    url: str | None = None
    title: str | None = None
    description: str | None = None
    author: str | None = None
    published_date: str | None = None
    site_name: str | None = None
    image_url: str | None = None
    type: str | None = None
    retrieved_at: str | None = None
    doi: str | None = None
    isbn: str | None = None


class URLView(Model):
    url: str | None = None
    metadata: URLMetadata | None = None
    url_library_count: int | None = None
    url_connection_count: int | None = None
    url_in_library: bool | None = None
    url_is_connected: bool | None = None


class CardNote(Model):
    id: str | None = None
    text: str | None = None


class Collection(Model):
    id: str | None = None
    uri: str | None = None
    name: str | None = None
    author: User | None = None
    description: str | None = None
    access_type: str | None = None
    card_count: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    is_following: bool | None = None
    follower_count: int | None = None


class URLCard(Model):
    type: str | None = None
    id: str | None = None
    url: str | None = None
    uri: str | None = None
    card_content: Any = None
    library_count: int | None = None
    url_library_count: int | None = None
    url_in_library: bool | None = None
    url_is_connected: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    author: User | None = None
    note: CardNote | None = None
    collections: list[Collection] | None = None
    libraries: list[User] | None = None


class Connection(Model):
    id: str | None = None
    type: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    curator: User | None = None


class ConnectionView(Model):
    connection: Connection
    source: URLView | None = None
    target: URLView | None = None


class Activity(Model):
    id: str | None = None
    activity_type: str | None = None
    created_at: datetime | None = None
    user: User | None = None
    card: URLCard | None = None
    collections: list[Collection] | None = None
    connection: ConnectionView | None = None


class Notification(Model):
    id: str | None = None
    type: str | None = None
    created_at: datetime | None = None
    read: bool | None = None
    user: User | None = None
    card: URLCard | None = None
    collections: list[Collection] | None = None
    connection: ConnectionView | None = None
    follow_target_type: str | None = None
    follow_target_id: str | None = None


class NoteCard(Model):
    id: str | None = None
    note: str | None = None
    author: User | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LibraryEntry(Model):
    user: User
    card: URLCard | None = None


class URLStats(Model):
    library_count: int | None = None
    note_count: int | None = None
    collection_count: int | None = None
    connections: dict[str, dict[str, int]] | None = None


class URLMetadataResponse(Model):
    metadata: URLMetadata
    stats: URLStats | None = None


class AddURLResponse(Model):
    url_card_id: str
    note_card_id: str | None = None


class IDResponse(Model):
    card_id: str | None = None
    collection_id: str | None = None
    connection_id: str | None = None
    follow_id: str | None = None
    success: bool | None = None
    marked_count: int | None = None


class CountResponse(Model):
    count: int | None = None
    unread_count: int | None = None


ItemT = TypeVar("ItemT")

# the api names its result array differently per endpoint (cards, users,
# activities, ...). collect whichever is present into `items` so every
# paginated response has one stable shape.
_ITEM_KEYS = (
    "items",
    "cards",
    "collections",
    "users",
    "urls",
    "libraries",
    "notes",
    "activities",
    "actors",
    "connections",
    "notifications",
)


class Page(Model, Generic[ItemT]):
    items: list[ItemT] = Field(default_factory=list)
    pagination: Pagination | None = None
    sorting: Any = None
    unread_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _collect_items(cls, data: Any) -> Any:
        if isinstance(data, dict) and "items" not in data:
            for key in _ITEM_KEYS:
                if isinstance(data.get(key), list):
                    return {**data, "items": data[key]}
        return data

    def __iter__(self) -> Any:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)


class CollectionDetail(Collection):
    url_cards: list[URLCard] | None = None
    pagination: Pagination | None = None
    sorting: Any = None
