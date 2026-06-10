"""command-line interface for semble.

requires the `cli` extra: `uv add 'semble-api[cli]'` (or `uvx --from 'semble-api[cli]' semble`).
"""

try:
    import cyclopts
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "the semble cli requires the `cli` extra: uv add 'semble-api[cli]'"
    ) from exc

import semble
from semble import Semble, SembleError

app = cyclopts.App(
    name="semble",
    help="interact with semble (semble.so) from the terminal",
    version=semble.__version__,
)


@app.command
def whoami() -> None:
    """show my profile and unread notification count."""
    with Semble() as client:
        me = client.actors.get_my_profile(include_stats=True)
        print(f"@{me.handle} ({me.name})")
        print(f"  cards: {me.url_card_count}")
        print(f"  collections: {me.collection_count}")
        print(f"  connections: {me.connection_count}")
        print(f"  followers: {me.follower_count} / following: {me.following_count}")

        unread = client.notifications.get_unread_count()
        count = unread.unread_count if unread.unread_count is not None else unread.count
        print(f"  unread notifications: {count}")


@app.command
def feed(limit: int = 10, *, following: bool = False) -> None:
    """show recent activity from the global (or following) feed."""
    with Semble() as client:
        get = client.feeds.get_following if following else client.feeds.get_global
        for activity in get(limit=limit):
            when = f"{activity.created_at:%m-%d %H:%M}" if activity.created_at else "?"
            who = f"@{activity.user.handle}" if activity.user else "?"
            what = activity.card.url if activity.card else ""
            print(f"{when}  {activity.activity_type:<22} {who:<24} {what}")


@app.command
def search(query: str, limit: int = 10) -> None:
    """semantic search across semble."""
    with Semble() as client:
        for hit in client.search.semantic(query, limit=limit):
            title = (
                hit.metadata.title
                if hit.metadata and hit.metadata.title
                else "(untitled)"
            )
            print(f"{title}\n  {hit.url}\n")


@app.command
def library(handle: str | None = None, limit: int = 10) -> None:
    """list cards in a library — mine by default, or any user's."""
    with Semble() as client:
        if handle:
            page = client.cards.list_by_user(handle, limit=limit)
        else:
            page = client.cards.list_mine(limit=limit)

        for card in page:
            note = f"  [note: {card.note.text}]" if card.note and card.note.text else ""
            print(f"{card.id}  {card.url}{note}")

        if page.pagination and page.pagination.total_count is not None:
            print(f"\n{len(page)} of {page.pagination.total_count} cards")


@app.command
def add(
    url: str,
    *,
    note: str | None = None,
    collection: list[str] | None = None,
) -> None:
    """add a url to my library, optionally with a note and collection ids."""
    with Semble() as client:
        added = client.cards.add_url(url, note=note, collection_ids=collection)
        print(f"added {url}")
        print(f"  url card: {added.url_card_id}")
        if added.note_card_id:
            print(f"  note card: {added.note_card_id}")


@app.command
def rm(card_id: str) -> None:
    """remove a card from my library."""
    with Semble() as client:
        client.cards.remove_from_library(card_id)
        print(f"removed {card_id}")


def main() -> None:
    try:
        app()
    except SembleError as exc:
        raise SystemExit(f"error: {exc}") from exc


if __name__ == "__main__":
    main()
