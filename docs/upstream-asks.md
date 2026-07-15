# upstream asks for cosmik-network/semble

grounded in the backend source (github.com/cosmik-network/semble) while
operating phi's library at real usage, 2026-07-13/15. each of these cost us a
production incident or a design workaround; none is speculative.

## 1. cascade deletes (or referential refusal)

deleting a collection leaves every `collectionLink` and `connection`
referencing it dangling on curators' repos forever — nothing cleans them up.
phi's 2026-07-14 reorg orphaned 43 of 54 connections and 14 of 33 links this
way. either cascade (delete referencing links/edges server-side and publish
the removals) or refuse to delete a referenced collection until it's empty.

## 2. unique collection names per curator

`create_collection` has no uniqueness constraint on (curator, name). two
concurrent check-then-create code blocks raced and created duplicate
"Games"/"games" collections (2026-07-14). client-side serialization works
around it, but the constraint belongs in the backend.

## 3. standalone NOTE cards as first-class creations

the api can only create url-anchored cards (`save_card` / `addUrl`). NOTE
cards written raw to the PDS (the only way to make one) never gain library
membership, so they can be neither collected ("Card must be published in
curator's library") nor found by library search. either expose note-card
creation or reconcile firehose-observed cards into library membership.

## 4. typed connection endpoints (or document the constraint)

the `network.cosmik.connection` lexicon says source/target are any "URL
string or AT URI", but the backend types endpoints as url-or-card.
collection-to-collection edges are lexicon-legal and index-dead — phi wrote
23 before we understood this. tighten the lexicon description, or support
collection endpoints for real.

## 5. (feature) nested collections

collections are flat at every layer today (no parent field, no COLLECTION
card type, no nesting api). fine for small libraries; at world-model scale a
`domain / thing` naming convention is carrying the hierarchy that structure
should. a parent ref on the collection record would let appviews render real
trees without breaking flat readers.
