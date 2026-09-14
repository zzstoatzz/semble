# most-saved URL shared by two collections

live task implemented in `src/collection-task.ts`.

## question

which URL present in both of two specified collections has the most saves across Semble?

this combines collection comparison with a precise popularity measure. popularity means the number of libraries containing the URL, not collection followers, collection membership count, or references. there is no time-window claim.

## inputs and prompt

selected through the live search API on 2026-09-12 UTC:

- `collection_a`: `ca9cbf0b-fc76-43e5-a676-05a7262b08a9` — [atproto things by tyler.fun](https://semble.so/profile/tyler.fun/collections/3mhbpdg2gpc2r)
- `collection_b`: `21d2b63c-2131-412a-b9b8-13aa6f6637d7` — [atproto tools ⚒️ by wesleyfinck.org](https://semble.so/profile/wesleyfinck.org/collections/3m3tfl4fcfe2k)

the discovery scan read every page and observed 79 and 51 distinct URLs, with four shared URLs and differing library counts. these observations establish suitability, not expected answers: recompute everything during each evaluated run. keep these same IDs for every model/server combination. record collection sizes and overlap size with each run so an empty or trivial case is visible.

```text
Compare Semble collections {{collection_a}} and {{collection_b}}.
Among the URLs present in BOTH collections, find the one saved in the
most libraries across Semble. If several tie for the highest count,
return any one of them. Identify the URL and its library save count.
If the collections share no URLs, say so.
Use current data and make only read-only calls.
```

the prompt specifies the outcome, not the tool sequence. both MCP servers receive the same prompt and ordinary harness limits. the model sees neither the checker results nor a computed candidate list.

## independent live check

the TypeScript fact checker calls the Semble XRPC API directly using the same account as the agent. it establishes ground truth without Pi or either MCP implementation. a separate Pi judge evaluates the natural-language answer against those facts, following the task-specific criteria pattern in Prefect's `evaluate_response` fixture.

1. read all pages of `network.cosmik.collection.get` for both collection IDs. verify pagination completed; an incomplete read is not an empty collection.
2. deduplicate each collection by the exact URL returned by Semble and calculate the intersection. do not invent URL normalization rules or compare user-specific card IDs.
3. for every shared URL, call `network.cosmik.card.getUrlMetadata` with `includeStats=true`. use `stats.libraryCount` as the authoritative save count. missing stats are a checker failure, not zero saves.
4. compute the maximum and the complete set of tied winners. an empty intersection has no winner.

perform the check before and after each agent run. compare collection URL sets and the shared URLs' save counts. if either changed, or either check failed, mark the outcome inconclusive with its reason. this detects observed drift; the API does not provide an atomic snapshot, so identical before/after observations cannot prove nothing changed in between. retain timestamps and responses as evidence, never as frozen inputs for future runs.

## verdicts

- **pass:** the judge confirms the final answer identifies a winning URL and its exact save count, or explicitly states there is no overlap when that is true. prose, Markdown, and code fences are acceptable.
- **fail:** stable, complete checker observations but a missing/wrong count, a non-winning URL, or a contradictory final conclusion.
- **inconclusive:** observed data drift or unavailable/incomplete checker data. exclude from the correctness denominator and report separately.
- **fail, execution:** timeout, output-token limit, turn limit, provider error, or other execution failure. these count as failed evals, with the execution status retained to explain why. a run that cannot finish within the shared budget does not pass.

the judge model is configured separately in the matrix and is identical across compared runs. it receives the task, candidate answer, and computed winner set, without the actor's model or MCP identity. its only tool is `submit_verdict`, which validates a boolean `passed` and a textual `reason`. judge failure is inconclusive. judge traces and usage are stored separately, so grading cost does not count toward either actor's performance.

never retry a stable wrong answer until it passes. any later retry policy must retain every attempt and distinguish inconclusive-data retries from model repetitions. empty-overlap passes are reported separately because they do not exercise popularity ranking.

## measurements

correctness is the primary measure. retain the existing agent tokens, estimated cost, turns, tool errors, and elapsed time. record checker requests and elapsed time separately so validation overhead is not charged to either MCP's agent performance. annotate comparisons with the actual collection sizes, overlap, and observed drift; live runs across days need not have identical difficulty.

## run

```sh
just evals run --task collection-overlap-popularity
```

add `--model haiku` or `--server code-mode` to narrow the matrix. each run writes `checker-before.json`, `checker-after.json`, `judge.json`, `judge-events.jsonl`, and `evaluation.json` beside its Pi trace and execution result. checker requests have their own 60-second observation timeout and pagination completeness checks. invalid or missing data yields an inconclusive verdict rather than an invented zero.

## sources

- [collections API](https://docs.cosmik.network/semble-api/collections.md): collection cards and pagination
- [cards API](https://docs.cosmik.network/semble-api/cards.md): URL metadata with `stats.libraryCount`
