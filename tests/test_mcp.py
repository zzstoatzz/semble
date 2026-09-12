import asyncio
import json
from typing import Any

import httpx2 as httpx
import pytest
from fastmcp import Client

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
