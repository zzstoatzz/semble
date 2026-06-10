"""atproto record shapes for the network.cosmik.* lexicons.

these model the records as they live on a pds, separate from the app-view
dtos in `semble.types`. useful when reading or writing semble records
directly (e.g. with pdsx or the atproto sdk) instead of going through the
api.
"""

from typing import Any

from pydantic import Field

from semble.types import Model

RECORD_TYPE_CARD = "network.cosmik.card"
RECORD_TYPE_URL_CONTENT = "network.cosmik.card#urlContent"
RECORD_TYPE_NOTE_CONTENT = "network.cosmik.card#noteContent"
RECORD_TYPE_COLLECTION = "network.cosmik.collection"
RECORD_TYPE_COLLECTION_LINK = "network.cosmik.collectionLink"
RECORD_TYPE_PROVENANCE = "network.cosmik.defs#provenance"

CARD_TYPE_URL = "URL"
CARD_TYPE_NOTE = "NOTE"


class StrongRef(Model):
    """an atproto strong reference: an at-uri plus the record cid."""

    uri: str
    cid: str


class URLMetadataRecord(Model):
    record_type: str | None = Field(default=None, alias="$type")
    content_type: str | None = Field(default=None, alias="type")
    title: str | None = None
    description: str | None = None
    author: str | None = None
    site_name: str | None = None
    image_url: str | None = None
    published_date: str | None = None
    retrieved_at: str | None = None


class URLContentRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_URL_CONTENT, alias="$type")
    url: str
    metadata: URLMetadataRecord | None = None


class NoteContentRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_NOTE_CONTENT, alias="$type")
    text: str


class ProvenanceRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_PROVENANCE, alias="$type")
    via: StrongRef | None = None


class CardRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_CARD, alias="$type")
    card_type: str = Field(alias="type")
    content: Any = None
    url: str | None = None
    parent_card: StrongRef | None = None
    created_at: str
    provenance: ProvenanceRecord | None = None


class CollectionRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_COLLECTION, alias="$type")
    name: str
    description: str | None = None
    created_at: str


class CollectionLinkRecord(Model):
    record_type: str = Field(default=RECORD_TYPE_COLLECTION_LINK, alias="$type")
    card: StrongRef
    collection: StrongRef
    created_at: str
