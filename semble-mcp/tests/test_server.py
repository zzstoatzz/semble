import httpx2 as httpx
from fastmcp import Client
from semble_mcp import build_server

from semble import Semble


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
        result = await session.call_tool("search", {"query": "semantic search urls"})
        assert "search_semantic" in result.content[0].text


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
