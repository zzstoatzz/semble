"""list cards in a library — mine by default, or any user's.

usage: uv run scripts/library.py [handle] [limit]
"""

import sys

from semble import Semble

handle = sys.argv[1] if len(sys.argv) > 1 else None
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

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
