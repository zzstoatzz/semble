"""code-mode mcp server over the semble sdk.

instead of one mcp tool per endpoint, the full sdk surface is registered
host-side and hidden behind fastmcp's CodeMode transform — clients see only
`search` / `get_schema` / `execute`, and compose sdk calls as python running
in a monty sandbox.
"""

import inspect

from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode

from semble import Semble
from semble.resources._base import SyncResource


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
            mcp.tool(method, name=f"{resource_name}_{name}", tags={resource_name})
    return mcp


def main() -> None:
    build_server().run()
