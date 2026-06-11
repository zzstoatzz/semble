# Prefect curate adoption gap: connection lookup/delete by AT URI

`my-prefect-server` is moving phi's curation flow from direct `network.cosmik.*`
record writes to `semble-api`.

Most mutation paths map cleanly:

- URL cards: `cards.add_url`, `cards.update_url_associations`,
  `cards.remove_from_library`
- collections: `collections.create`, `collections.delete`
- collection links: resolved as URL-card collection associations
- connections: `connections.create`

The remaining gap is deleting or updating an existing connection when the agent
starts from the public AT URI, e.g.
`at://did:plc:.../network.cosmik.connection/...`.

Current SDK/API shape:

- `semble.records` exports card, collection, and collection-link record
  constants/models, but no connection record constant/model
- `connections.list_by_user(...)` returns `ConnectionView`
- `ConnectionView.connection` includes `id`, `type`, `note`, timestamps, and
  curator fields
- it does not expose the source connection record `uri`
- `connections.delete(...)` requires the internal `connection_id`

That means Prefect can create connections through Semble, but cannot faithfully
translate an existing AT URI into the Semble connection ID needed for delete or
update without keeping a raw PDS fallback.

Suggested upstream fix:

- include the backing AT URI on `Connection`, or
- add `connections.get_by_at_uri(uri)` / `connections.delete_by_at_uri(uri)`.

Once that exists, `flows/curate.py` can remove its explicit "cannot resolve
connection id" branch and route connection deletes through Semble like the rest
of the curation mutations.
