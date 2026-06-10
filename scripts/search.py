"""semantic search across semble.

usage: uv run scripts/search.py <query> [limit]
"""

import sys

from semble import Semble

if len(sys.argv) < 2:
    sys.exit(__doc__.strip())

query = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10

with Semble() as client:
    for hit in client.search.semantic(query, limit=limit):
        title = (
            hit.metadata.title if hit.metadata and hit.metadata.title else "(untitled)"
        )
        print(f"{title}\n  {hit.url}\n")
