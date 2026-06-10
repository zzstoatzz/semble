import json
from typing import Any

import httpx2

from semble.types import CollectionDetail, Page, URLCard
from tests.conftest import AsyncClientFactory, SyncClientFactory


def body_of(request: httpx2.Request) -> dict[str, Any]:
    return json.loads(request.content)


def test_add_url_posts_body(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({"urlCardId": "card_1", "noteCardId": "note_1"})
    result = client.cards.add_url(
        "https://x.io", note="neat", collection_ids=["col_1"], via_card_id=None
    )
    assert recorder.last.method == "POST"
    assert str(recorder.last.url).endswith("/network.cosmik.card.addUrl")
    assert body_of(recorder.last) == {
        "url": "https://x.io",
        "note": "neat",
        "collectionIds": ["col_1"],
    }
    assert result.url_card_id == "card_1"
    assert result.note_card_id == "note_1"


def test_list_mine_params(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({"cards": [], "pagination": {"hasMore": False}})
    page = client.cards.list_mine(
        page=2, limit=10, sort_by="createdAt", sort_order="desc"
    )
    params = recorder.last.url.params
    assert params["page"] == "2"
    assert params["limit"] == "10"
    assert params["sortBy"] == "createdAt"
    assert params["sortOrder"] == "desc"
    assert "urlType" not in params
    assert isinstance(page, Page)


def test_list_mine_parses_cards(sync_client: SyncClientFactory) -> None:
    client, _ = sync_client(
        {
            "cards": [
                {
                    "id": "c1",
                    "url": "https://x.io",
                    "createdAt": "2026-06-10T12:00:00Z",
                    "author": {"handle": "zzstoatzz.io"},
                }
            ],
            "pagination": {"currentPage": 1, "totalPages": 1, "hasMore": False},
        }
    )
    page = client.cards.list_mine()
    card = page.items[0]
    assert isinstance(card, URLCard)
    assert card.author is not None
    assert card.author.handle == "zzstoatzz.io"
    assert card.created_at is not None
    assert card.created_at.year == 2026


def test_collection_get_detail(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client(
        {
            "id": "col_1",
            "name": "reading list",
            "urlCards": [{"id": "c1"}],
            "pagination": {"hasMore": True},
        }
    )
    detail = client.collections.get("col_1", url_type="article")
    assert isinstance(detail, CollectionDetail)
    assert recorder.last.url.params["collectionId"] == "col_1"
    assert recorder.last.url.params["urlType"] == "article"
    assert detail.url_cards is not None
    assert detail.url_cards[0].id == "c1"
    assert detail.pagination is not None
    assert detail.pagination.has_more is True


def test_connection_types_repeat_param(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({"connections": []})
    client.connections.get_for_url(
        "https://x.io", connection_types=["SUPPORTS", "OPPOSES"], direction="outgoing"
    )
    params = recorder.last.url.params
    assert params.get_list("connectionTypes") == ["SUPPORTS", "OPPOSES"]
    assert params["direction"] == "outgoing"


def test_update_note_returns_none(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({})
    assert client.cards.update_note("card_1", "new note") is None
    assert body_of(recorder.last) == {"cardId": "card_1", "note": "new note"}


def test_follow(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({"followId": "f1", "success": True})
    result = client.graph.follow("did:plc:abc", "USER")
    assert body_of(recorder.last) == {"targetId": "did:plc:abc", "targetType": "USER"}
    assert result.follow_id == "f1"
    assert result.success is True


def test_mark_all_read_posts_empty_body(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client({"markedCount": 4})
    result = client.notifications.mark_all_read()
    assert body_of(recorder.last) == {}
    assert result.marked_count == 4


def test_semantic_search(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client(
        {"urls": [{"url": "https://x.io", "metadata": {"title": "x"}}]}
    )
    page = client.search.semantic("durable execution", threshold=0.7, limit=5)
    params = recorder.last.url.params
    assert params["query"] == "durable execution"
    assert params["threshold"] == "0.7"
    assert params["limit"] == "5"
    hit = page.items[0]
    assert hit.metadata is not None
    assert hit.metadata.title == "x"


def test_get_url_metadata(sync_client: SyncClientFactory) -> None:
    client, recorder = sync_client(
        {
            "metadata": {"url": "https://x.io", "title": "x"},
            "stats": {"libraryCount": 2},
        }
    )
    result = client.cards.get_url_metadata("https://x.io", include_stats=True)
    assert recorder.last.url.params["includeStats"] == "true"
    assert result.metadata.title == "x"
    assert result.stats is not None
    assert result.stats.library_count == 2


async def test_async_add_url(async_client: AsyncClientFactory) -> None:
    client, recorder = async_client({"urlCardId": "card_1"})
    result = await client.cards.add_url("https://x.io")
    assert body_of(recorder.last) == {"url": "https://x.io"}
    assert result.url_card_id == "card_1"


async def test_async_list_by_user(async_client: AsyncClientFactory) -> None:
    client, recorder = async_client({"cards": [{"id": "c1"}]})
    page = await client.cards.list_by_user(
        "pdewey.com", url_type="article", uncollected=False
    )
    params = recorder.last.url.params
    assert params["identifier"] == "pdewey.com"
    assert params["urlType"] == "article"
    assert params["uncollected"] == "false"
    assert page.items[0].id == "c1"


async def test_async_get_profile(async_client: AsyncClientFactory) -> None:
    client, recorder = async_client({"handle": "zzstoatzz.io", "followerCount": 1})
    user = await client.actors.get_profile("zzstoatzz.io", include_stats=True)
    assert recorder.last.url.params["identifier"] == "zzstoatzz.io"
    assert user.follower_count == 1
