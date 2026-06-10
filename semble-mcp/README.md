# semble-mcp

code-mode mcp server for [semble](https://semble.so), built on [fastmcp](https://gofastmcp.com)'s [CodeMode transform](https://gofastmcp.com/servers/transforms/code-mode).

instead of one mcp tool per api endpoint, the full [semble-api](https://pypi.org/project/semble-api/) sdk surface (49 methods) is registered host-side and hidden behind three meta-tools:

- `search` — find sdk methods by keyword
- `get_schema` — fetch parameter schemas for specific methods
- `execute` — run model-written python in a [monty](https://github.com/pydantic/monty) sandbox, composing methods via `await call_tool(...)`

intermediate results stay in the sandbox; only the final answer returns to the model's context.

## usage

```bash
claude mcp add semble -- uvx semble-mcp
```

auth comes from `SEMBLE_API_KEY` (environment or `.env`, via the sdk's settings). without a key the server runs against public read endpoints only.

## development

from the workspace root:

```bash
just test
```

the server is a reflection loop over the sdk — new endpoints wrapped in `semble-api` appear here automatically.
