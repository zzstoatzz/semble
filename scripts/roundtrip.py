"""exercise the write paths end to end, cleaning up after itself.

WARNING: this writes real records to your semble account (and pds) before
removing them. run it deliberately:

    uv run scripts/roundtrip.py
"""

from semble import Semble

URL = "https://example.com"

with Semble() as client:
    print("adding url to library...")
    added = client.cards.add_url(URL, note="semble-api roundtrip test")
    print(f"  url card: {added.url_card_id}, note card: {added.note_card_id}")

    card = client.cards.get(added.url_card_id)
    print(f"  fetched: {card.url} (in library: {card.url_in_library})")

    print("creating collection...")
    created = client.collections.create(
        "semble-api roundtrip",
        description="temporary — created by scripts/roundtrip.py",
    )
    collection_id = created.collection_id
    print(f"  collection: {collection_id}")

    print("adding card to collection...")
    client.cards.update_url_associations(
        added.url_card_id, add_to_collections=[collection_id]
    )
    detail = client.collections.get(collection_id)
    in_collection = [c.id for c in detail.url_cards or []]
    print(f"  collection now has: {in_collection}")

    print("updating note...")
    client.cards.update_note(added.url_card_id, "updated by roundtrip")

    print("cleaning up...")
    client.collections.delete(collection_id)
    client.cards.remove_from_library(added.url_card_id)
    print("done — collection deleted, card removed")
