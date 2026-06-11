# semble for agents

this package ships three surfaces for the same api: a python sdk, a cli, and an mcp server. they share one auth story (`SEMBLE_API_KEY` from the environment or a `.env`; without it, public reads only) and one underlying client — the differences are about *where your agent runs and what it can touch*. this doc is for people wiring semble into agents, not for people developing this repo.

## at a glance

| surface | install | the agent is... |
| ------- | ------- | --------------- |
| sdk     | `uv add semble-api` | python you're writing (scripts, pydantic-ai tools, pipelines) |
| cli     | `uv add 'semble-api[cli]'` / `uvx` | something with a shell (claude code, codex, a cron job) |
| mcp     | `claude mcp add semble -e SEMBLE_API_KEY=... -- uvx --from 'semble-api[mcp]' semble-mcp` | an mcp client, especially one without a shell (claude desktop, cursor) |

## the sdk

the substrate everything else is built on. typed sync/async clients over all ~50 `network.cosmik.*` endpoints, pydantic models on every response, snake_case in / camelCase on the wire, and an escape hatch (`client.get(nsid, params)`) for anything unwrapped.

```python
from semble import Semble

with Semble() as client:
    for hit in client.search.semantic("agent memory", limit=5):
        print(hit.url)
```

use it when the agent *is* your code: tool functions in an agent framework, batch curation jobs, anything where you want validation errors before the network and real types after it. this is also the surface to build new surfaces from — the mcp server below is ~40 lines over it.

## the cli

`semble` is machine-readable by default, which makes it an agent tool as much as a human one: lists are ndjson, single results are one json object, keys are the api's camelCase. no flags needed to make it parseable — `--pretty` is the opt-in for humans, not the other way around.

```bash
semble search "durable execution" | jq -r '.url'
semble add https://example.com --note "worth a read"
semble library pdewey.com
```

if your agent already has shell access, this is usually the right surface: zero integration work, composes with `jq`/`xargs`/everything, and each invocation is a fresh process with no session to manage. an agent that can run bash needs nothing else to read and write semble.

## the mcp server

`semble-mcp` exposes the sdk to mcp clients via [fastmcp code mode](https://gofastmcp.com/servers/transforms/code-mode). instead of one tool per endpoint (which puts ~50 schemas in the model's context before any work happens), clients see three meta-tools:

- `search` — find sdk methods by keyword
- `get_schema` — fetch parameter schemas for chosen methods
- `execute` — run model-written python in a [monty](https://github.com/pydantic/monty) sandbox, composing methods via `await call_tool("cards_search", {...})`

the payoff is composition without context cost: a workflow like "semantic search, then fetch who saved each hit, then summarize" is one `execute` block and one result in context, instead of n tool round-trips each hauling intermediate json through the model. params use the sdk's snake_case names (discover them via `get_schema` — don't guess), and mistakes come back as precise pydantic validation errors the model can fix in-loop, before anything hits the network.

prefer it when:

- the client has no shell (claude desktop, cursor, most hosted agents) — mcp is the only door, and three tools beat fifty
- workflows are composition-heavy and context economy matters, even if a shell exists
- you want the tool surface to track the sdk automatically — the server reflects over the client, so new sdk methods appear without anyone maintaining tool definitions

know the caveats: mcp client quality varies a lot in practice (see [mcpval](https://dev-log.prefect.io/mcpval/) — judge a server by what your client can actually accomplish with it, not by what it exposes). auth works both ways: stdio launches read `SEMBLE_API_KEY` from the environment, while a hosted (http) deployment resolves auth per request from an `x-semble-api-key` header — the server holds no identity, so one shared url serves many users, each bringing their own key (no header = public reads).

## choosing

the short version: **shell → cli, your own python → sdk, neither → mcp.** code mode is the exception that can earn its place alongside a shell, when multi-call composition would otherwise drag intermediate results through context.

one thing that is *not* a differentiator: capability. all three surfaces carry the full read/write power of the api key behind them. pick by runtime fit, not by trying to use the surface as a permission boundary — if you want an agent restricted to reads, give it no key (public reads work) rather than a narrower surface.

## writes are public

semble is a social knowledge graph on atproto: cards, notes, collections, and connections your agent creates are real records, visible to the network and attributed to the account behind the key. that's the point — shared curation trails are what make the graph worth reading — but it means an agent writing to semble is publishing, not journaling.

a few norms keep the graph high-signal:

- write with intent: a url with a note saying *why* beats ten bare urls
- curate into collections rather than dumping into the library root
- connections (`supports`, `opposes`, `explains`, ...) are claims — make them when the relationship is real, not to inflate linkage
- cleanup is part of write access: `remove_from_library`, `collections.delete`, and friends work the same as the adds

for the wider picture of agents as curators, see [semble + agents](https://nate.leaflet.pub/3mnxnia4lvk2n).
