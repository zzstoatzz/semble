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

EXECUTE_DESCRIPTION = """Execute a SELF-CONTAINED Python program against the Semble SDK.

FIRST call the MCP search tool directly to discover SDK tools. Do NOT start
with execute to discover tools: await call_tool("search", ...) always fails.

This is a stateless function, NOT a notebook or terminal:
- Every invocation starts empty. Variables, imports, and fetched data from any
  previous invocation DO NOT EXIST. Never refer to a previous call's variables.
- Only the returned value is sent back to you. print() output is DISCARDED.
  End your program with an explicit return containing the actual useful result.
  Returning {"status": "done"} does not expose anything you printed or computed.
- To use fetched data, fetch AND process it within the SAME invocation. If you
  need another call, fetch again or explicitly include the small data you need.
  Do not manually transcribe large API responses into Python literals.

Workflow:
1. Discover tool names and inspect their exact input and output schemas using
   search or get_schema directly. Prefer search to select relevant schema fields.
   Do not guess tool names, argument names, response fields, or pagination fields.
2. Inside execute, use await call_tool("sdk_tool_name", {"argument": value}).
   Only underlying SDK tools are callable here. search, get_schema, and execute
   are NOT SDK tools and cannot be called through call_tool.
3. Fetch the data, follow pagination until complete, and perform filtering,
   deduplication, comparisons, counting, sorting, or aggregation in Python.
   A requested limit does not prove all records were returned: check pagination.
   SDK pagination uses current_page, total_pages, total_count, and has_more
   (snake_case). It does NOT use has_next_page. Inspect the actual returned
   pagination; missing/None fields are unknown, not proof there are no more pages.
   len(response["items"]) counts ONE PAGE, not the total number of matches!
   For total counts use pagination.total_count when supplied, or fetch every page.
   For membership/comparison tasks, a total count alone cannot replace fetching
   every page. These rules apply to EACH paginated endpoint you call.
4. Return a SMALL computed result that directly supports your answer, including
   relevant identifiers and counts. Do not return entire collections or lists
   of records just to compare them by reading the model context yourself.
5. Write the final answer from the returned values. Do not invent missing counts
   or substitute zero when a field is missing. If data is unclear, inspect only
   keys or one small sample, then run a new self-contained computation.

Valid example (fetch and return in ONE call):
r = await call_tool("notifications_get_unread_count", {})
return {"unread": r["count"]}

Counting example for any SDK response with items and pagination:
p = response["pagination"]
if p["total_count"] is not None:
    count = p["total_count"]
else:
    # Fetch remaining pages using the inspected endpoint's page/cursor arguments
    # and completion fields before counting. Do not assume len(items) is total.
    raise ValueError("Inspect pagination and fetch remaining pages before counting")
return {"count": count}

Invalid: print(r) without returning it; referring to r in the next execute call;
calling await call_tool("search", ...); returning full API responses instead of
computing over them. Use basic Python operations; Monty is a limited Python
sandbox, not a full Python installation. SDK results are already Python values,
so you usually do not need JSON encoding or decoding.
Use list comprehensions and indexing, not next(generator_expression): Monty
does not provide normal Python generator semantics. For a first match, build
matches = [x for x in values if condition] and use matches[0] after checking
that matches is nonempty.
For sort/max/min keys use a lambda, e.g. max(counts, key=lambda k: counts[k]),
not a bound method such as key=counts.get (unsupported in Monty).
"""


def executable_search(get_catalog: GetToolCatalog) -> Tool:
    """Build discovery against the current, access-filtered SDK catalog."""
    sandbox = MontySandboxProvider(
        limits={"max_duration_secs": 5.0, "max_memory": 100_000_000}
    )

    async def search(code: str, ctx: Context) -> str:
        """Search SDK metadata with Python; explicitly return the data you need.

        `tools` is a dict keyed by tool name. Each value has name, description
        (optional), tags (list), inputSchema, and outputSchema (optional).
        Inspect this dictionary with tools.keys() or tools.items(), not dir()
        or reflection: tool names are dictionary keys, not Python globals.
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
        transforms=[
            CodeMode(
                discovery_tools=[executable_search, GetSchemas()],
                execute_description=EXECUTE_DESCRIPTION,
            )
        ],
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
