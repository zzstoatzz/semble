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
from functools import wraps

try:
    from fastmcp import FastMCP
    from fastmcp.experimental.transforms.code_mode import CodeMode
    from fastmcp.server.dependencies import get_http_headers
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "the semble mcp server requires the `mcp` extra: uv add 'semble-api[mcp]'"
    ) from exc

from semble import Semble
from semble.resources._base import SyncResource

API_KEY_HEADER = "x-semble-api-key"


def _per_request(default_method, resource_name: str, method_name: str):
    """wrap a bound sdk method so each call resolves its client.

    `get_http_headers()` returns `{}` off-http (stdio, in-memory tests), so
    the fallback path dispatches straight to the process-default client.
    """

    @wraps(default_method)
    def tool(*args, **kwargs):
        key = get_http_headers().get(API_KEY_HEADER)
        if not key:
            return default_method(*args, **kwargs)
        with Semble(api_key=key) as client:
            method = getattr(getattr(client, resource_name), method_name)
            return method(*args, **kwargs)

    return tool


def build_server(client: Semble | None = None) -> FastMCP:
    client = client or Semble()
    mcp = FastMCP("semble", transforms=[CodeMode()])
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
