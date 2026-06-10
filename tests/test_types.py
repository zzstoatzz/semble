from semble.records import CardRecord, StrongRef
from semble.types import Notification, Page, Pagination, URLCard, User


def test_page_collects_cards_key():
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


def test_page_collects_users_key():
    page = Page[User].model_validate({"users": [{"handle": "zzstoatzz.io"}]})
    assert page.items[0].handle == "zzstoatzz.io"


def test_page_prefers_explicit_items():
    page = Page[User].model_validate(
        {"items": [{"handle": "a"}], "users": [{"handle": "b"}]}
    )
    assert [u.handle for u in page] == ["a"]


def test_page_unread_count():
    page = Page[Notification].model_validate({"notifications": [], "unreadCount": 3})
    assert page.unread_count == 3
    assert page.items == []


def test_page_is_iterable():
    page = Page[User].model_validate({"users": [{"handle": "a"}, {"handle": "b"}]})
    assert [u.handle for u in page] == ["a", "b"]


def test_camel_case_aliases():
    user = User.model_validate({"avatarUrl": "https://cdn/x.png", "followerCount": 2})
    assert user.avatar_url == "https://cdn/x.png"
    assert user.follower_count == 2


def test_unknown_fields_allowed():
    user = User.model_validate({"handle": "x", "someNewField": 1})
    assert user.handle == "x"


def test_pagination_defaults():
    assert Pagination().next_cursor is None


def test_card_record_round_trip():
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


def test_strong_ref():
    ref = StrongRef(uri="at://did:plc:x/network.cosmik.card/y", cid="bafy...")
    assert ref.model_dump() == {
        "uri": "at://did:plc:x/network.cosmik.card/y",
        "cid": "bafy...",
    }
