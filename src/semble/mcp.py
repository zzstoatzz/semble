"""code-mode mcp server over the semble sdk.

instead of one mcp tool per endpoint, the full sdk surface is registered
host-side and hidden behind fastmcp's CodeMode transform — clients see only
`search` / `get_schema` / `execute`, and compose sdk calls as python running
in a monty sandbox.

auth is per-request: if a call arrives over http with an `x-semble-api-key`
header, that key is used for the sdk calls it triggers — so one hosted server
can serve many users without holding anyone's identity. without the header
(stdio, or a keyless deployment) it falls back to the process-level client,
which reads `SEMBLE_API_KEY` from the environment or serves public reads.

requires the `mcp` extra: `uv add 'semble-api[mcp]'`.
"""

import inspect
import json
from collections.abc import Callable
from functools import wraps

try:
    from fastmcp import Context, FastMCP
    from fastmcp.experimental.transforms.code_mode import (
        CodeMode,
        GetSchemas,
        GetToolCatalog,
        MontySandboxProvider,
    )
    from fastmcp.server.dependencies import get_http_headers
    from fastmcp.tools import Tool
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "semble-mcp needs fastmcp>=3.4.2 with code mode support "
        f"(install via the `mcp` extra: uv add 'semble-api[mcp]'). import failed: {exc}"
    ) from exc

from semble import Semble
from semble.resources._base import SyncResource

API_KEY_HEADER = "x-semble-api-key"


def executable_search(get_catalog: GetToolCatalog) -> Tool:
    """Build discovery against the current, access-filtered SDK catalog."""
    sandbox = MontySandboxProvider(
        limits={"max_duration_secs": 5.0, "max_memory": 100_000_000}
    )

    async def search(code: str, ctx: Context) -> str:
        """Search SDK metadata with Python; explicitly return the data you need.

        `tools` is a dict keyed by tool name. Each value has name, description
        (optional), tags (list), inputSchema, and outputSchema (optional).
        Schemas are JSON Schema: nested $ref values resolve within that schema's
        $defs. Filter by names, tags, descriptions, or schema fields and project
        only useful data. No ranking or result limit is applied automatically.

        Examples:
        return [n for n, t in tools.items() if "collections" in t["tags"]]
        return tools["collections_get"]["inputSchema"]
        return {n: t.get("outputSchema") for n, t in tools.items() if "libraries" in n}

        Return JSON-compatible data; the result is serialized as JSON text,
        including [] for no matches. Each call has fresh state.
        Only catalog data is available: no call_tool,
        SDK, network, filesystem, or credentials. Use execute for SDK calls.
        Runs in Monty (limited Python), with a 5-second / 100 MB budget.
        """
        catalog = await get_catalog(ctx)
        tools = {
            tool.name: {
                **tool.to_mcp_tool().model_dump(
                    mode="json", by_alias=True, exclude_none=True
                ),
                "tags": sorted(tool.tags),
            }
            for tool in catalog
        }
        result = await sandbox.run(code, inputs={"tools": tools})
        return json.dumps(result, ensure_ascii=False, allow_nan=False)

    return Tool.from_function(fn=search, name="search")


def _per_request[**P, R](
    default_method: Callable[P, R], resource_name: str, method_name: str
) -> Callable[P, R]:
    """wrap a bound sdk method so each call resolves its client.

    `get_http_headers()` returns `{}` off-http (stdio, in-memory tests), so
    the fallback path dispatches straight to the process-default client.
    """

    @wraps(default_method)
    def tool(*args: P.args, **kwargs: P.kwargs) -> R:
        key = get_http_headers().get(API_KEY_HEADER)
        if not key:
            return default_method(*args, **kwargs)
        with Semble(api_key=key) as client:
            method: Callable[P, R] = getattr(
                getattr(client, resource_name), method_name
            )
            return method(*args, **kwargs)

    return tool


def build_server(client: Semble | None = None) -> FastMCP:
    client = client or Semble()
    mcp = FastMCP(
        "semble",
        transforms=[CodeMode(discovery_tools=[executable_search, GetSchemas()])],
    )
    resources = {
        name: attr
        for name, attr in vars(client).items()
        if isinstance(attr, SyncResource)
    }
    for resource_name, resource in sorted(resources.items()):
        for name, method in inspect.getmembers(resource, inspect.ismethod):
            if name.startswith("_"):
                continue
            mcp.tool(
                _per_request(method, resource_name, name),
                name=f"{resource_name}_{name}",
                tags={resource_name},
            )
    return mcp


def main() -> None:
    build_server().run()
