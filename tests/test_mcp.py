import asyncio
import json
from typing import Any

import httpx2 as httpx
import pytest
from fastmcp import Client, FastMCP

from semble import Semble
from semble.mcp import build_server


def mock_semble(payload: dict) -> Semble:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return Semble(
        api_key="test-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


async def test_clients_see_only_code_mode_tools() -> None:
    async with Client(build_server(mock_semble({}))) as session:
        names = sorted(tool.name for tool in await session.list_tools())
        assert names == ["execute", "get_schema", "search"]


async def test_search_surfaces_sdk_methods() -> None:
    async with Client(build_server(mock_semble({}))) as session:
        result = await session.call_tool(
            "search", {"code": 'return [n for n in tools if "semantic" in n]'}
        )
        assert "search_semantic" in result.content[0].text


async def test_search_projects_real_schemas_without_sdk_requests() -> None:
    from tests.conftest import Recorder

    recorder = Recorder({})
    client = Semble(
        api_key="catalog-must-not-contain-this",
        http_client=httpx.Client(transport=httpx.MockTransport(recorder.handler)),
    )
    async with Client(build_server(client)) as session:
        result = await session.call_tool(
            "search", {"code": 'return tools["collections_get"]'}
        )
        text = result.content[0].text
        tool = json.loads(text)
        assert tool["tags"] == ["collections"]
        assert tool["inputSchema"]["required"] == ["collection_id"]
        assert "url_cards" in tool["outputSchema"]["properties"]
        assert "catalog-must-not-contain-this" not in text
        result = await session.call_tool(
            "search",
            {
                "code": 'return [n for n, t in tools.items() if "collections" in t["tags"]]'
            },
        )
        assert "collections_get" in result.content[0].text
        assert "notifications_" not in result.content[0].text
    assert recorder.requests == []


async def test_search_has_fresh_catalog_and_respects_visibility() -> None:
    server = build_server(mock_semble({}))
    async with Client(server) as session:
        await session.call_tool("search", {"code": "tools.clear()\nreturn len(tools)"})
        result = await session.call_tool(
            "search", {"code": 'return "collections_get" in tools'}
        )
        assert result.content[0].text == "true"
        server.disable(names={"collections_get"})
        result = await session.call_tool(
            "search", {"code": 'return "collections_get" in tools'}
        )
        assert result.content[0].text == "false"


@pytest.mark.parametrize(
    "code",
    [
        'return await call_tool("notifications_get_unread_count", {})',
        'return open("/etc/passwd").read()',
        "import socket\nreturn socket.socket()",
        'return __import__("os").environ',
        'return tools["missing_tool"]',
        "this is invalid python!",
        "while True:\n    pass",
        'return "x" * 200_000_000',
    ],
)
async def test_search_rejects_unsafe_or_invalid_code_and_recovers(code: str) -> None:
    async with Client(build_server(mock_semble({}))) as session:
        result = await session.call_tool("search", {"code": code}, raise_on_error=False)
        assert result.is_error
        result = await session.call_tool(
            "search", {"code": 'return [n for n in tools if n == "missing_tool"]'}
        )
        assert result.content[0].text == "[]"


async def test_search_concurrent_calls_are_independent() -> None:
    async with Client(build_server(mock_semble({}))) as session:
        results = await asyncio.gather(
            *[
                session.call_tool("search", {"code": f"tools.clear()\nreturn {i}"})
                for i in range(4)
            ]
        )
        assert [r.content[0].text for r in results] == ["0", "1", "2", "3"]
        result = await session.call_tool("search", {"code": "return len(tools) > 0"})
        assert result.content[0].text == "true"


async def test_get_schema_exposes_sdk_signature() -> None:
    async with Client(build_server(mock_semble({}))) as session:
        result = await session.call_tool("get_schema", {"tools": ["search_semantic"]})
        text = result.content[0].text
        assert "query" in text
        assert "threshold" in text


async def test_execute_composes_sdk_calls() -> None:
    async with Client(build_server(mock_semble({"count": 7}))) as session:
        code = (
            'unread = await call_tool("notifications_get_unread_count", {})\n'
            'return unread["count"] * 2\n'
        )
        result = await session.call_tool("execute", {"code": code})
        assert result.content[0].text == "14"


async def test_api_key_header_routes_to_fresh_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """an x-semble-api-key header gets its own client; the default sees nothing."""
    from tests.conftest import Recorder

    default_recorder = Recorder({"count": 1})
    default_client = Semble(
        api_key="sk_process",
        http_client=httpx.Client(
            transport=httpx.MockTransport(default_recorder.handler)
        ),
    )

    per_request_recorder = Recorder({"count": 7})

    def fake_semble(api_key: str | None = None, **kwargs: Any) -> Semble:
        return Semble(
            api_key=api_key,
            http_client=httpx.Client(
                transport=httpx.MockTransport(per_request_recorder.handler)
            ),
        )

    monkeypatch.setattr("semble.mcp.Semble", fake_semble)
    monkeypatch.setattr(
        "semble.mcp.get_http_headers", lambda: {"x-semble-api-key": "sk_user"}
    )

    async with Client(build_server(default_client)) as session:
        code = (
            'unread = await call_tool("notifications_get_unread_count", {})\n'
            'return unread["count"]\n'
        )
        result = await session.call_tool("execute", {"code": code})

    assert result.content[0].text == "7"
    assert default_recorder.requests == []
    assert per_request_recorder.last.headers["x-api-key"] == "sk_user"


async def test_no_header_falls_back_to_process_client() -> None:
    """off-http (or headerless) calls dispatch to the client given at build time."""
    from tests.conftest import Recorder

    recorder = Recorder({"count": 3})
    default_client = Semble(
        api_key="sk_process",
        http_client=httpx.Client(transport=httpx.MockTransport(recorder.handler)),
    )

    async with Client(build_server(default_client)) as session:
        code = (
            'unread = await call_tool("notifications_get_unread_count", {})\n'
            'return unread["count"]\n'
        )
        result = await session.call_tool("execute", {"code": code})

    assert result.content[0].text == "3"
    assert recorder.last.headers["x-api-key"] == "sk_process"


async def test_every_catalog_tool_has_a_description() -> None:
    """discovery filters on descriptions; a blank one hides the method from the model."""
    async with Client(build_server(mock_semble({}))) as session:
        result = await session.call_tool(
            "search",
            {
                "code": "return sorted(n for n, t in tools.items() if not t.get('description'))"
            },
        )
        assert json.loads(result.content[0].text) == []


async def test_nested_call_timeout_is_short_and_named(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """a stalled endpoint fails fast inside execute and says which method stalled."""
    from semble.mcp import NESTED_CALL_TIMEOUT

    seen: dict[str, Any] = {}

    def stalled(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out", request=request)

    def fake_semble(api_key: str | None = None, **kwargs: Any) -> Semble:
        seen.update(kwargs)
        return Semble(
            api_key=api_key,
            http_client=httpx.Client(transport=httpx.MockTransport(stalled)),
        )

    monkeypatch.setattr("semble.mcp.Semble", fake_semble)
    monkeypatch.setattr(
        "semble.mcp.get_http_headers", lambda: {"x-semble-api-key": "sk_user"}
    )

    async with Client(build_server(mock_semble({}))) as session:
        code = (
            'r = await call_tool("search_get_accounts", {"q": "zzstoatzz"})\nreturn r\n'
        )
        result = await session.call_tool(
            "execute", {"code": code}, raise_on_error=False
        )

    assert result.is_error
    text = result.content[0].text
    assert "search_get_accounts" in text
    assert f"within {NESTED_CALL_TIMEOUT:g}s" in text
    assert seen["timeout"] == NESTED_CALL_TIMEOUT
    assert NESTED_CALL_TIMEOUT < 30


def test_default_client_uses_nested_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    from semble.mcp import NESTED_CALL_TIMEOUT

    seen: dict[str, Any] = {}

    def fake_semble(**kwargs: Any) -> Semble:
        seen.update(kwargs)
        return mock_semble({})

    monkeypatch.setattr("semble.mcp.Semble", fake_semble)
    build_server()
    assert seen["timeout"] == NESTED_CALL_TIMEOUT


async def test_schema_exposes_sort_by_values() -> None:
    async with Client(build_server(mock_semble({}))) as session:
        result = await session.call_tool(
            "search",
            {
                "code": "return tools['cards_list_by_user']['inputSchema']['properties']['sort_by']"
            },
        )
        assert "libraryCount" in result.content[0].text


# --- jev mode ---------------------------------------------------------------


class _FakeJev:
    """answers every choice with equal probabilities and every noul with yes."""

    def __init__(self) -> None:
        self.requests = 0

    async def system_one(self, state: Any, questions: Any) -> Any:
        self.requests += 1
        answers: dict[str, Any] = {}
        for qid, question in questions.items():
            if question["type"] == "choice":
                names = list(question["criteria"])
                share = 1 / len(names)
                answers[qid] = type(
                    "A",
                    (),
                    {"choice": names[0], "probabilities": dict.fromkeys(names, share)},
                )()
            else:
                answers[qid] = type("A", (), {"noul": 0.9})()
        return type("R", (), {"answers": answers})()


def _jev_server(monkeypatch: pytest.MonkeyPatch, **limits: float) -> FastMCP:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-typesafe-key")
    for name, value in limits.items():
        monkeypatch.setattr(f"semble.mcp.{name}", value)
    return build_server(mock_semble({}), mode="jev")


async def test_jev_mode_exposes_search_and_call_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async with Client(_jev_server(monkeypatch)) as session:
        names = {tool.name for tool in await session.list_tools()}
    assert names == {"search_tools", "call_tool"}


def test_jev_mode_is_selected_by_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TYPESAFE_API_KEY", "test-typesafe-key")
    monkeypatch.setenv("SEMBLE_MCP_MODE", "jev")
    server = build_server(mock_semble({}))
    assert {t.name for t in asyncio.run(server.list_tools())} == {
        "search_tools",
        "call_tool",
    }
    monkeypatch.setenv("SEMBLE_MCP_MODE", "nope")
    with pytest.raises(SystemExit):
        build_server(mock_semble({}))


def test_jev_mode_without_a_typesafe_key_fails_at_startup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY"):
        build_server(mock_semble({}), mode="jev")


async def test_jev_mode_rate_limits_a_client(monkeypatch: pytest.MonkeyPatch) -> None:
    server = _jev_server(
        monkeypatch,
        JEV_CLIENT_REQUESTS_PER_SECOND=0.001,
        JEV_CLIENT_BURST=3,
        JEV_GLOBAL_REQUESTS_PER_SECOND=1000,
        JEV_GLOBAL_BURST=1000,
    )
    async with Client(server) as session:
        for _ in range(2):
            await session.list_tools()
        with pytest.raises(Exception, match="Rate limit exceeded"):
            for _ in range(10):
                await session.list_tools()


async def test_jev_mode_rate_limits_the_whole_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    server = _jev_server(
        monkeypatch,
        JEV_CLIENT_REQUESTS_PER_SECOND=1000,
        JEV_CLIENT_BURST=1000,
        JEV_GLOBAL_REQUESTS_PER_SECOND=0.001,
        JEV_GLOBAL_BURST=3,
    )
    async with Client(server) as session:
        with pytest.raises(Exception, match="Global rate limit exceeded"):
            for _ in range(10):
                await session.list_tools()


def test_rate_limit_buckets_are_keyed_by_api_key_hash() -> None:
    from semble.mcp import _rate_limit_client_id

    # outside a request there are no headers: everyone shares the anonymous bucket
    assert _rate_limit_client_id(None) == "anonymous"
