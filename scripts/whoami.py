"""sanity-check auth: show my profile and unread notification count.

usage: uv run scripts/whoami.py
"""

from semble import Semble

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
