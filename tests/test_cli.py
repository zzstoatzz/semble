import json
import sys
from typing import Any, Protocol

import httpx2
import pytest

import semble.cli as cli
from semble import Semble

# maps a substring of the request url (usually the nsid method) to the
# json the mock api should return for it
Responses = dict[str, Any]


class CliSetup(Protocol):
    def __call__(
        self, responses: Responses, status_code: int = 200
    ) -> "RouteRecorder": ...


class RouteRecorder:
    def __init__(self, responses: Responses, status_code: int = 200) -> None:
        self.responses = responses
        self.status_code = status_code
        self.requests: list[httpx2.Request] = []

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        for fragment, payload in self.responses.items():
            if fragment in str(request.url):
                return httpx2.Response(self.status_code, json=payload)
        return httpx2.Response(404, json={"message": f"no mock for {request.url}"})

    @property
    def last(self) -> httpx2.Request:
        return self.requests[-1]


@pytest.fixture
def cli_routes(monkeypatch: pytest.MonkeyPatch) -> CliSetup:
    def setup(responses: Responses, status_code: int = 200) -> RouteRecorder:
        recorder = RouteRecorder(responses, status_code)
        http = httpx2.Client(transport=httpx2.MockTransport(recorder.handler))
        client = Semble(api_key="sk_test", http_client=http)
        monkeypatch.setattr(cli, "Semble", lambda: client)
        return recorder

    return setup


def invoke(capsys: pytest.CaptureFixture[str], *tokens: str) -> list[str]:
    """run the cli in-process and return non-empty stdout lines."""
    cli.app(list(tokens), result_action="return_value")
    out = capsys.readouterr().out
    return [line for line in out.splitlines() if line.strip()]


def test_whoami_json(cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]) -> None:
    cli_routes(
        {
            "getMyProfile": {"handle": "bufo.uk", "urlCardCount": 3},
            "getUnreadCount": {"unreadCount": 2},
        }
    )
    lines = invoke(capsys, "whoami")
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["profile"]["handle"] == "bufo.uk"
    assert data["profile"]["urlCardCount"] == 3
    assert data["unreadNotifications"] == 2


def test_whoami_pretty(
    cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]
) -> None:
    cli_routes(
        {
            "getMyProfile": {"handle": "bufo.uk", "name": "nate"},
            "getUnreadCount": {"unreadCount": 0},
        }
    )
    lines = invoke(capsys, "whoami", "--pretty")
    assert lines[0] == "@bufo.uk (nate)"


def test_feed_ndjson(cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]) -> None:
    cli_routes(
        {
            "feed.getGlobal": {
                "activities": [
                    {
                        "activityType": "CARD_COLLECTED",
                        "user": {"handle": "a.com"},
                        "card": {"url": "https://x.io"},
                    },
                    {
                        "activityType": "CARD_COLLECTED",
                        "user": {"handle": "b.com"},
                        "card": {"url": "https://y.io"},
                    },
                ]
            }
        }
    )
    lines = invoke(capsys, "feed", "2")
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["user"]["handle"] == "a.com"
    assert first["card"]["url"] == "https://x.io"


def test_feed_following_flag(
    cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]
) -> None:
    recorder = cli_routes({"feed.getFollowing": {"activities": []}})
    invoke(capsys, "feed", "--following")
    assert "feed.getFollowing" in str(recorder.last.url)
    assert recorder.last.url.params["limit"] == "10"


def test_search_ndjson(
    cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]
) -> None:
    recorder = cli_routes(
        {
            "search.semantic": {
                "urls": [{"url": "https://x.io", "metadata": {"title": "x"}}]
            }
        }
    )
    lines = invoke(capsys, "search", "durable execution", "5")
    assert recorder.last.url.params["query"] == "durable execution"
    assert recorder.last.url.params["limit"] == "5"
    assert json.loads(lines[0])["metadata"]["title"] == "x"


def test_library_mine_vs_user(
    cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]
) -> None:
    recorder = cli_routes(
        {
            "card.listMine": {"cards": [{"id": "c1", "url": "https://x.io"}]},
            "card.listByUser": {"cards": [{"id": "c2", "url": "https://y.io"}]},
        }
    )
    lines = invoke(capsys, "library")
    assert "card.listMine" in str(recorder.last.url)
    assert json.loads(lines[0])["id"] == "c1"

    lines = invoke(capsys, "library", "pdewey.com")
    assert "card.listByUser" in str(recorder.last.url)
    assert recorder.last.url.params["identifier"] == "pdewey.com"
    assert json.loads(lines[0])["id"] == "c2"


def test_add_json(cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]) -> None:
    recorder = cli_routes(
        {"card.addUrl": {"urlCardId": "card_1", "noteCardId": "note_1"}}
    )
    lines = invoke(
        capsys, "add", "https://x.io", "--note", "neat", "--collection", "col_1"
    )
    body = json.loads(recorder.last.content)
    assert body == {"url": "https://x.io", "note": "neat", "collectionIds": ["col_1"]}
    data = json.loads(lines[0])
    assert data["urlCardId"] == "card_1"
    assert data["noteCardId"] == "note_1"


def test_rm_json(cli_routes: CliSetup, capsys: pytest.CaptureFixture[str]) -> None:
    recorder = cli_routes({"card.removeFromLibrary": {}})
    lines = invoke(capsys, "rm", "card_1")
    assert json.loads(recorder.last.content) == {"cardId": "card_1"}
    assert json.loads(lines[0]) == {"cardId": "card_1", "removed": True}


# this test runs the real entry point, so cyclopts warns about sys.exit
# under pytest — that exit behavior is exactly what's being tested
@pytest.mark.filterwarnings("ignore::UserWarning")
def test_api_error_exits_nonzero(
    cli_routes: CliSetup, monkeypatch: pytest.MonkeyPatch
) -> None:
    cli_routes({"getMyProfile": {"message": "bad key"}}, status_code=401)
    monkeypatch.setattr(sys, "argv", ["semble", "whoami"])
    with pytest.raises(SystemExit) as excinfo:
        cli.main()
    assert "bad key" in str(excinfo.value)
