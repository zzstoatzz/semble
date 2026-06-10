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

## examples

runnable demos live in `scripts/`:

```bash
uv run scripts/whoami.py                      # auth sanity check
uv run scripts/feed.py 10                     # global feed (--following for yours)
uv run scripts/library.py pdewey.com          # someone's library
uv run scripts/search.py "durable execution"  # semantic search
uv run scripts/roundtrip.py                   # write-path exercise (mutates your account!)
```

## development

```bash
just test   # pytest
just fmt    # ruff format + check
just check  # ty
```

## see also

- [semble api docs](https://docs.cosmik.network/semble-api)
- [@semble.so/api](https://npmx.dev/package/@semble.so/api) — official typescript client
- [tangled.org/pdewey.com/semble](https://tangled.org/pdewey.com/semble) — go client
