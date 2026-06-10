"""show recent activity from the global (or following) feed.

usage: uv run scripts/feed.py [limit]
       uv run scripts/feed.py --following [limit]
"""

import sys

from semble import Semble

args = [a for a in sys.argv[1:] if not a.startswith("-")]
following = "--following" in sys.argv
limit = int(args[0]) if args else 10

with Semble() as client:
    feed = client.feeds.get_following if following else client.feeds.get_global
    for activity in feed(limit=limit):
        when = f"{activity.created_at:%m-%d %H:%M}" if activity.created_at else "?"
        who = f"@{activity.user.handle}" if activity.user else "?"
        what = activity.card.url if activity.card else ""
        print(f"{when}  {activity.activity_type:<22} {who:<24} {what}")
