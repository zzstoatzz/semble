# semble-api

python client for the [semble](https://semble.so) api — collaborative bookmarking and knowledge curation on [atproto](https://atproto.com).

built on [httpx2](https://github.com/pydantic/httpx2) and [pydantic](https://docs.pydantic.dev), with sync and async clients.

## installation

```bash
uv add semble-api
```

## quick start

create an api key at [semble.so/settings/api-keys](https://semble.so/settings/api-keys), then:

```python
from semble import Semble

client = Semble()  # reads SEMBLE_API_KEY from the environment or a local .env

# add a url to your library
result = client.cards.add_url("https://example.com", note="worth a read")

# search your cards
for card in client.cards.search("durable execution"):
    print(card.url)

# semantic search across semble
for hit in client.search.semantic("agent memory", threshold=0.7):
    print(hit.metadata.title, hit.url)
```

async is the same surface:

```python
from semble import AsyncSemble

async with AsyncSemble() as client:
    profile = await client.actors.get_my_profile(include_stats=True)
    feed = await client.feeds.get_following(limit=25)
```

## api surface

resources mirror the `network.cosmik.*` xrpc namespaces:

| namespace             | what's there                                                       |
| --------------------- | ------------------------------------------------------------------ |
| `client.cards`        | add/search/list urls and notes, metadata, library status            |
| `client.collections`  | create/update/delete collections, followers, contributors           |
| `client.connections`  | typed links between urls (supports, opposes, explains, ...)         |
| `client.feeds`        | global and following activity feeds                                 |
| `client.notifications`| list, unread count, mark read                                       |
| `client.search`       | semantic search, similar urls, account search                       |
| `client.actors`       | profiles                                                            |
| `client.graph`        | follow/unfollow users and collections                               |

every endpoint not yet wrapped is reachable via the escape hatch:

```python
client.get("network.cosmik.card.getLibraryStatus", {"url": "https://example.com"})
```

`semble.records` has pydantic models for the raw `network.cosmik.*` pds records, if you're reading or writing them directly (e.g. with [pdsx](https://github.com/zzstoatzz/pdsx)).

## configuration

settings come from explicit kwargs, then `SEMBLE_*` environment variables, then a local `.env` file (via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)):

| setting           | kwarg      | default                       |
| ----------------- | ---------- | ----------------------------- |
| `SEMBLE_API_KEY`  | `api_key`  | unauthenticated (public reads work) |
| `SEMBLE_BASE_URL` | `base_url` | `https://api.semble.so/xrpc`  |
| `SEMBLE_TIMEOUT`  | `timeout`  | `30.0`                        |

the api key is held as a pydantic `SecretStr`, so it won't leak into logs or reprs.

## cli

a small [cyclopts](https://github.com/BrianPugh/cyclopts) cli ships as an extra:

```bash
uv add 'semble-api[cli]'
# or run without installing
uvx --from 'semble-api[cli]' semble --help

semble whoami                          # auth sanity check
semble feed 10 --following             # activity feeds
semble search "durable execution"      # semantic search
semble library pdewey.com              # anyone's library (or yours, with no handle)
semble add https://example.com --note "worth a read"
semble rm <card-id>
```

output is machine-readable by default — lists are ndjson, single results are one json object, keys match the api's camelCase — so it pipes straight into jq or an agent. add `--pretty` to any command for human-formatted output:

```bash
semble feed 25 | jq -r '.card.url'
semble search "agent memory" | jq -r '.metadata.title'
semble feed --pretty
```

## mcp server

the `mcp` extra ships a `semble-mcp` entry point that exposes this sdk to mcp clients via [fastmcp code mode](https://gofastmcp.com/servers/transforms/code-mode): three meta-tools (`search` / `get_schema` / `execute`) instead of one tool per endpoint, with model-written python composing sdk calls in a [monty](https://github.com/pydantic/monty) sandbox. intermediate results stay in the sandbox; only the final answer returns to the model's context.

create an api key at [semble.so/settings/api-keys](https://semble.so/settings/api-keys), then:

```bash
claude mcp add semble -e SEMBLE_API_KEY=your-key -- uvx --from 'semble-api[mcp]' semble-mcp
```

for other mcp clients (claude desktop, cursor, ...), the equivalent json config:

```json
{
  "mcpServers": {
    "semble": {
      "command": "uvx",
      "args": ["--from", "semble-api[mcp]", "semble-mcp"],
      "env": { "SEMBLE_API_KEY": "your-key" }
    }
  }
}
```

the key is optional — without it the server is limited to public reads. the server also picks up `SEMBLE_API_KEY` from the environment or a `.env` in the working directory, so inside a checkout of this repo a plain `claude mcp add semble -- uv run --directory /path/to/this/repo semble-mcp` works too.

hosted (http) deployments resolve auth per request instead: send your key as an `x-semble-api-key` header and it's used only for the calls that request triggers — one shared server url serves many users without holding anyone's identity. no header means public reads. a hosted instance runs at `https://semble.fastmcp.app/mcp`:

```bash
claude mcp add semble --transport http https://semble.fastmcp.app/mcp -H "x-semble-api-key: your-key"
```

`requirements.horizon.txt` exists for hosting platforms whose builders can't install extras from pyproject.toml.

## examples

`scripts/roundtrip.py` exercises the write paths end to end (add url → note → collection → cleanup). it mutates your real account, so run it deliberately:

```bash
uv run scripts/roundtrip.py
```

## development

```bash
just test   # pytest
just fmt    # ruff format + check
just check  # ty
```

## see also

- [semble for agents](docs/agent-surfaces.md) — choosing between the sdk, cli, and mcp surfaces when wiring up agents
- [semble api docs](https://docs.cosmik.network/semble-api)
- [@semble.so/api](https://npmx.dev/package/@semble.so/api) — official typescript client
- [tangled.org/pdewey.com/semble](https://tangled.org/pdewey.com/semble) — go client
