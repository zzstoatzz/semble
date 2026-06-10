import httpx2
import pytest

from semble import (
    APIStatusError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    Semble,
    ServerError,
)


def test_api_key_header(sync_client):
    client, recorder = sync_client({"count": 0})
    client.notifications.get_unread_count()
    assert recorder.last.headers["x-api-key"] == "sk_test"
    assert recorder.last.headers["accept"] == "application/json"


def test_no_api_key_no_header(sync_client):
    client, recorder = sync_client({"count": 0}, api_key="")
    client.notifications.get_unread_count()
    assert "x-api-key" not in recorder.last.headers


def test_api_key_from_env(monkeypatch):
    monkeypatch.setenv("SEMBLE_API_KEY", "sk_from_env")
    assert Semble().api_key == "sk_from_env"


def test_base_url_from_env(monkeypatch):
    monkeypatch.setenv("SEMBLE_BASE_URL", "https://example.com/xrpc/")
    assert Semble().base_url == "https://example.com/xrpc"


def test_default_base_url(monkeypatch):
    monkeypatch.delenv("SEMBLE_BASE_URL", raising=False)
    assert Semble().base_url == "https://api.semble.so/xrpc"


def test_nsid_url(sync_client):
    client, recorder = sync_client({"count": 0})
    client.notifications.get_unread_count()
    assert (
        str(recorder.last.url)
        == "https://api.semble.so/xrpc/network.cosmik.notification.getUnreadCount"
    )


def test_escape_hatch_returns_raw_json(sync_client):
    client, recorder = sync_client({"anything": True})
    assert client.get(
        "network.cosmik.card.getLibraryStatus", {"url": "https://x.io"}
    ) == {"anything": True}
    assert recorder.last.url.params["url"] == "https://x.io"


def test_context_manager(sync_client):
    client, _ = sync_client({})
    with client as c:
        assert c is client


async def test_async_context_manager(async_client):
    client, _ = async_client({})
    async with client as c:
        assert c is client


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (400, APIStatusError),
        (401, AuthenticationError),
        (404, NotFoundError),
        (429, RateLimitError),
        (500, ServerError),
        (503, ServerError),
    ],
)
def test_error_mapping(sync_client, status_code, expected):
    client, _ = sync_client({"message": "nope"}, status_code=status_code)
    with pytest.raises(expected) as excinfo:
        client.notifications.get_unread_count()
    assert excinfo.value.status_code == status_code
    assert excinfo.value.message == "nope"


def test_error_message_from_error_key(sync_client):
    client, _ = sync_client({"error": "bad thing"}, status_code=400)
    with pytest.raises(APIStatusError, match="bad thing"):
        client.notifications.get_unread_count()


def test_error_message_from_plain_text():
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(500, text="oops")

    client = Semble(
        api_key="sk_test",
        http_client=httpx2.Client(transport=httpx2.MockTransport(handler)),
    )
    with pytest.raises(ServerError, match="oops"):
        client.notifications.get_unread_count()


async def test_async_error_mapping(async_client):
    client, _ = async_client({"message": "expired"}, status_code=401)
    with pytest.raises(AuthenticationError, match="expired"):
        await client.notifications.get_unread_count()
