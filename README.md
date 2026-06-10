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

[`semble-mcp`](semble-mcp/) — a workspace sibling — exposes this sdk to mcp clients via [fastmcp code mode](https://gofastmcp.com/servers/transforms/code-mode): three meta-tools (`search` / `get_schema` / `execute`) instead of 49, with model-written python composing sdk calls in a sandbox.

```bash
claude mcp add semble -- uv run --directory /path/to/this/repo semble-mcp
```

## examples

`scripts/roundtrip.py` exercises the write paths end to end (add url → note → collection → cleanup). it mutates your real account, so run it deliberately:

```bash
uv run scripts/roundtrip.py
```

## development

this repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/): `semble-api` at the root, `semble-mcp` as a member.

```bash
just test   # pytest (both packages)
just fmt    # ruff format + check
just check  # ty
```

## see also

- [semble api docs](https://docs.cosmik.network/semble-api)
- [@semble.so/api](https://npmx.dev/package/@semble.so/api) — official typescript client
- [tangled.org/pdewey.com/semble](https://tangled.org/pdewey.com/semble) — go client
