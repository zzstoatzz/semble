from semble.records import CardRecord, StrongRef
from semble.types import Notification, Page, Pagination, URLCard, User


def test_page_collects_cards_key() -> None:
    page = Page[URLCard].model_validate(
        {
            "cards": [{"id": "abc", "url": "https://x.io"}],
            "pagination": {"currentPage": 1, "hasMore": False},
        }
    )
    assert len(page) == 1
    assert page.items[0].id == "abc"
    assert page.pagination is not None
    assert page.pagination.has_more is False


def test_page_collects_users_key() -> None:
    page = Page[User].model_validate({"users": [{"handle": "zzstoatzz.io"}]})
    assert page.items[0].handle == "zzstoatzz.io"


def test_page_prefers_explicit_items() -> None:
    page = Page[User].model_validate(
        {"items": [{"handle": "a"}], "users": [{"handle": "b"}]}
    )
    assert [u.handle for u in page] == ["a"]


def test_page_unread_count() -> None:
    page = Page[Notification].model_validate({"notifications": [], "unreadCount": 3})
    assert page.unread_count == 3
    assert page.items == []


def test_page_is_iterable() -> None:
    page = Page[User].model_validate({"users": [{"handle": "a"}, {"handle": "b"}]})
    assert [u.handle for u in page] == ["a", "b"]


def test_camel_case_aliases() -> None:
    user = User.model_validate({"avatarUrl": "https://cdn/x.png", "followerCount": 2})
    assert user.avatar_url == "https://cdn/x.png"
    assert user.follower_count == 2


def test_unknown_fields_allowed() -> None:
    user = User.model_validate({"handle": "x", "someNewField": 1})
    assert user.handle == "x"


def test_pagination_defaults() -> None:
    assert Pagination().next_cursor is None


def test_card_record_round_trip() -> None:
    record = CardRecord.model_validate(
        {
            "$type": "network.cosmik.card",
            "type": "URL",
            "content": {
                "$type": "network.cosmik.card#urlContent",
                "url": "https://x.io",
            },
            "url": "https://x.io",
            "createdAt": "2026-06-10T00:00:00Z",
        }
    )
    assert record.record_type == "network.cosmik.card"
    assert record.card_type == "URL"
    dumped = record.model_dump(by_alias=True, exclude_none=True)
    assert dumped["$type"] == "network.cosmik.card"
    assert dumped["type"] == "URL"


def test_strong_ref() -> None:
    ref = StrongRef(uri="at://did:plc:x/network.cosmik.card/y", cid="bafy...")
    assert ref.model_dump() == {
        "uri": "at://did:plc:x/network.cosmik.card/y",
        "cid": "bafy...",
    }


def test_url_metadata_coerces_numeric_scalars() -> None:
    from semble.types import URLMetadata

    metadata = URLMetadata.model_validate({"author": 262588213843476, "title": "t"})
    assert metadata.author == "262588213843476"
    assert metadata.title == "t"


def test_sort_by_is_an_enum_where_the_api_defines_one() -> None:
    import inspect
    from typing import get_args

    from semble.resources.cards import Cards
    from semble.resources.collections import Collections

    cards_sort = inspect.signature(Cards.list_by_user).parameters["sort_by"].annotation
    assert "libraryCount" in str(cards_sort) and get_args
    collections_sort = (
        inspect.signature(Collections.list_by_user).parameters["sort_by"].annotation
    )
    assert "cardCount" in str(collections_sort)


def test_url_card_content_is_typed_metadata() -> None:
    card = URLCard.model_validate(
        {
            "id": "c1",
            "url": "https://x.io",
            "cardContent": {"title": "t", "siteName": "s", "author": 42},
        }
    )
    assert card.card_content is not None
    assert card.card_content.title == "t"
    assert card.card_content.site_name == "s"
    assert card.card_content.author == "42"
