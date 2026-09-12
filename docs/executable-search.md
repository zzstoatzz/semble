# executable search

Semble's MCP exposes `search`, `get_schema`, and `execute`. Search accepts
`{"code": "..."}` instead of the previous text-query arguments. Existing callers
using `query`, `tags`, `detail`, or `limit` must update their search calls.
`get_schema` and `execute` retain FastMCP's existing contracts.

Search runs Python in a fresh Monty sandbox. Its only input is `tools`, a
dictionary keyed by SDK tool name. Values contain the actual MCP tool schemas
plus sorted resource tags. FastMCP supplies the current access-filtered catalog;
the discovery implementation does not maintain a second endpoint inventory.
It passes serialized data into Monty, with no SDK objects or external callbacks.

Find collection operations:

```python
return [n for n, t in tools.items() if "collections" in t["tags"]]
```

Inspect the exact parameters of an operation:

```python
return tools["collections_get"]["inputSchema"]
```

Select output field names without returning full nested schemas:

```python
return {
    n: list(tools[n]["outputSchema"]["properties"])
    for n in ["collections_get", "cards_get_libraries_for_url"]
}
```

Return JSON-compatible data explicitly. Results are JSON text, so an empty
selection returns `[]`. Schema fields use the names advertised by the MCP;
schemas containing `$ref` must be interpreted with their associated `$defs`.
There is no implicit ranking, result limit, or truncation. The caller chooses
what to return. Missing keys and invalid code produce tool errors; subsequent
calls start fresh. Search has a 5-second execution limit and 100 MB Monty memory
limit. These are sandbox limits, not end-to-end HTTP or response-size limits.
Use `execute` to call the SDK; search cannot call it, access credentials, or
perform network or filesystem operations.

## local validation, 2026-09-12 UTC

- `uv run pytest tests/ -x`: 77 passed, including 17 MCP tests.
- `uv run ruff check src/ tests/` and `uv run ty check`: passed.
- Actual Monty tests cover schema projection, resource tags, zero SDK requests
  during search, catalog mutation isolation, disabled-tool visibility, concurrent
  calls, unavailable API/filesystem/network functions, malformed code, missing
  keys, timeout, memory exhaustion, and successful calls after errors.
- Existing execution composition and process/per-request credential routing
  tests pass without changing the execution implementation.
- A local HTTP server using the Horizon entrypoint accepted five concurrent
  searches. All returned valid JSON. Collection names took 394 bytes, collection
  input schema 652 bytes, library output schemas 9,422 bytes, and selected output
  field names 279 bytes. Empty selection returned two bytes: `[]`.
- Through the same local HTTP server, an `execute` call read one card from the
  live public “atproto things” collection and returned its name and field names.
  This was a manual read-only smoke check, with no model or judge involved.

Raw local HTTP evidence is in the ignored
`evals/results/executable-search-smoke-2026-09-12/http-smoke.json`.
These checks establish implementation behavior, not model performance or
complete sandbox security. No deployment or agent evaluation was performed.
