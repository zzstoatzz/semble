"""command-line interface for semble.

machine-readable by default: lists are ndjson (one json object per line,
api-cased keys) and single results are one json object, so output pipes
straight into jq or an agent. pass --pretty for human-formatted output.

requires the `cli` extra: `uv add 'semble-api[cli]'`.
"""

import json
from typing import Any

try:
    import cyclopts
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "the semble cli requires the `cli` extra: uv add 'semble-api[cli]'"
    ) from exc

from pydantic import BaseModel

import semble
from semble import Semble, SembleError

app = cyclopts.App(
    name="semble",
    help="interact with semble (semble.so) from the terminal",
    version=semble.__version__,
)


def _dump(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(by_alias=True, exclude_none=True, mode="json")


def _emit(data: BaseModel | dict[str, Any]) -> None:
    if isinstance(data, BaseModel):
        data = _dump(data)
    print(json.dumps(data))


@app.command
def whoami(*, pretty: bool = False) -> None:
    """show my profile and unread notification count."""
    with Semble() as client:
        me = client.actors.get_my_profile(include_stats=True)
        unread = client.notifications.get_unread_count()
        count = unread.unread_count if unread.unread_count is not None else unread.count

        if not pretty:
            _emit({"profile": _dump(me), "unreadNotifications": count})
            return

        print(f"@{me.handle} ({me.name})")
        print(f"  cards: {me.url_card_count}")
        print(f"  collections: {me.collection_count}")
        print(f"  connections: {me.connection_count}")
        print(f"  followers: {me.follower_count} / following: {me.following_count}")
        print(f"  unread notifications: {count}")


@app.command
def feed(limit: int = 10, *, following: bool = False, pretty: bool = False) -> None:
    """show recent activity from the global (or following) feed."""
    with Semble() as client:
        get = client.feeds.get_following if following else client.feeds.get_global
        for activity in get(limit=limit):
            if not pretty:
                _emit(activity)
                continue
            when = f"{activity.created_at:%m-%d %H:%M}" if activity.created_at else "?"
            who = f"@{activity.user.handle}" if activity.user else "?"
            what = activity.card.url if activity.card else ""
            print(f"{when}  {activity.activity_type:<22} {who:<24} {what}")


@app.command
def search(query: str, limit: int = 10, *, pretty: bool = False) -> None:
    """semantic search across semble."""
    with Semble() as client:
        for hit in client.search.semantic(query, limit=limit):
            if not pretty:
                _emit(hit)
                continue
            title = (
                hit.metadata.title
                if hit.metadata and hit.metadata.title
                else "(untitled)"
            )
            print(f"{title}\n  {hit.url}\n")


@app.command
def library(
    handle: str | None = None, limit: int = 10, *, pretty: bool = False
) -> None:
    """list cards in a library — mine by default, or any user's."""
    with Semble() as client:
        if handle:
            page = client.cards.list_by_user(handle, limit=limit)
        else:
            page = client.cards.list_mine(limit=limit)

        for card in page:
            if not pretty:
                _emit(card)
                continue
            note = f"  [note: {card.note.text}]" if card.note and card.note.text else ""
            print(f"{card.id}  {card.url}{note}")

        if pretty and page.pagination and page.pagination.total_count is not None:
            print(f"\n{len(page)} of {page.pagination.total_count} cards")


@app.command
def add(
    url: str,
    *,
    note: str | None = None,
    collection: list[str] | None = None,
    pretty: bool = False,
) -> None:
    """add a url to my library, optionally with a note and collection ids."""
    with Semble() as client:
        added = client.cards.add_url(url, note=note, collection_ids=collection)

        if not pretty:
            _emit(added)
            return

        print(f"added {url}")
        print(f"  url card: {added.url_card_id}")
        if added.note_card_id:
            print(f"  note card: {added.note_card_id}")


@app.command
def rm(card_id: str, *, pretty: bool = False) -> None:
    """remove a card from my library."""
    with Semble() as client:
        client.cards.remove_from_library(card_id)

        if not pretty:
            _emit({"cardId": card_id, "removed": True})
            return

        print(f"removed {card_id}")


def main() -> None:
    try:
        app()
    except SembleError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
