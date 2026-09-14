# learning from Cloudflare code mode

This is a source study, completed September 12, 2026, before further evaluations or MCP changes. It compares Semble's deployed source and pinned FastMCP dependency with Cloudflare's production API MCP and reusable Code Mode SDK. No agent evaluations, replay benchmarks, runtime tests, deployments, or implementation changes were performed for this study. Following clarification of scope, direct discovery calls were made against both live MCPs; they inspected tool definitions only and did not invoke underlying account/data operations. Other sizes and behavior examples come from previously captured artifacts.

The most transferable idea is controlled disclosure: give the model a map of the available operations, let it inspect the exact data contract it needs, and keep intermediate API data in execution. Cloudflare provides useful examples of all three, but its production server and SDK implement them differently. A 51-tool Semble server does not need the infrastructure supporting thousands of Cloudflare endpoints.

## source boundaries

- Semble deployed commit: `b14ea4aad3e7fb84ec9df49402885028dadad0ce`. [Server](../src/semble/mcp.py), [SDK models](../src/semble/types.py), and [dependency pin](../pyproject.toml). The deployed commit pins `fastmcp[code-mode]==4.0.3`; the inspected local installation is also 4.0.3. Monty is transitive; this study does not establish the exact deployed Monty version.
- Cloudflare production MCP: [cloudflare/mcp at 1027dbd](https://github.com/cloudflare/mcp/tree/1027dbd2865fc1932120db42ed53749bc30d2af0), Apache-2.0. The repository documents `mcp.cloudflare.com`; the inspected revision is not a verified production deployment SHA.
- Cloudflare SDK: [cloudflare/agents at 43a58a1](https://github.com/cloudflare/agents/tree/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode), MIT. Its connector ranker, renderer, logging and truncation utilities are not automatically features of the production API MCP.
- [cloudflare/mcp-server-cloudflare](https://github.com/cloudflare/mcp-server-cloudflare) contains domain-specific servers and points to `cloudflare/mcp` for broad API code mode. Those domain-specific implementations are not the main comparison here.

All three Cloudflare repositories are cached under `~/.cache/checkouts/github.com/cloudflare/`. FastMCP owning modules are `experimental/transforms/code_mode.py`, `server/transforms/search/base.py`, and `server/transforms/search/bm25.py` in the local 4.0.3 installation.

## how our server actually works

`build_server()` reflects over public methods on synchronous SDK resource objects and registers their signatures as tools. `@wraps` carries the SDK method's metadata into the per-request auth wrapper. Resource names become tags; `CodeMode()` wraps that catalog with its defaults. This explains why SDK method documentation and typing directly affect discovery.

`search` uses BM25 over names, descriptions, top-level parameter names and parameter descriptions. It does not search output-schema fields or independently understand API semantics. Its tokenizer splits underscores and punctuation, but not camelCase; positive lexical matches can enter the result without satisfying a minimum query coverage. Tags filter before ranking. The default internal ranker returns at most 50 candidates; the call's `limit` slices those candidates afterward. Increasing that argument cannot enumerate the whole 51-tool catalog. The displayed count is returned results versus catalog size, not a complete count of query matches.

`get_schema` has three renderings. Detailed Markdown lists names, heuristic types and required markers. It omits field descriptions, enum members and nested object structure even when these exist in the underlying schema. Full JSON preserves the contract but includes large output models. Previously captured discovery for `collections_get` plus `cards_get_libraries_for_url` was 795 bytes detailed and 92,983 bytes full. Separately, `sort_by` is typed as an unconstrained string in the SDK itself: a renderer cannot recover enum values absent from that source.

`execute` creates a new Monty execution and exposes `call_tool`. FastMCP dispatches each nested call through its server, preserving the catalog/auth boundary, then unwraps structured output for the sandbox. Only the returned execution value becomes the MCP result; the wrapper does not capture print output. Variables do not persist between calls. The default description already requests a single block and `return`, but does not explicitly explain those two common traps.

The inspected defaults are 50 nested calls per execution, 30 seconds of configured Monty duration, and 100 MB memory. These are distinct from the harness's 120-second actor timeout and per-response model token budget. Source configuration alone does not establish how all external I/O waits are charged by the deployed native runtime.

## what Cloudflare's production MCP does

[Search](https://github.com/cloudflare/mcp/blob/1027dbd2865fc1932120db42ed53749bc30d2af0/src/tools/search.ts) runs model-written JavaScript against `spec.paths` in a fresh isolate with outbound network disabled. There is no lexical ranker in this API search path. The description supplies types, a sample product directory, and examples that return endpoint summaries, request bodies, or parameters selectively.

[Spec preprocessing](https://github.com/cloudflare/mcp/blob/1027dbd2865fc1932120db42ed53749bc30d2af0/src/spec-processor.ts) preserves descriptions and response schemas, resolves references inline with circular markers, and derives product tags from paths. The full spec stays outside model context until code returns part of it. Inlining is a convenience for selection, not inherently compression; returning an entire resolved operation can still be large.

[Execute](https://github.com/cloudflare/mcp/blob/1027dbd2865fc1932120db42ed53749bc30d2af0/src/tools/execute.ts) also creates a fresh isolate. It supplies a typed request interface and an async-function example. Tokens stay in a host outbound proxy that restricts destinations. Account-selection machinery resolves identity when possible and provides specific corrective instructions when it cannot. Semble already keeps credentials host-side through its SDK callback; the lesson is to preserve that boundary, not import Cloudflare's account model.

Neither production handler establishes persistent user variables or returns captured console output. Therefore Cloudflare's production implementation is not evidence that persistence or stdout solves our problems. Its examples make the execution contract more concrete.

[Production output bounding](https://github.com/cloudflare/mcp/blob/1027dbd2865fc1932120db42ed53749bc30d2af0/src/truncate.ts) slices text at 24,000 characters and adds a warning to narrow the query. That bounds exposure but can split JSON. Its [retry helper](https://github.com/cloudflare/mcp/blob/1027dbd2865fc1932120db42ed53749bc30d2af0/src/utils/fetch-retry.ts) handles 429s and network errors with backoff. That is API-specific resilience machinery, not a discovery improvement; replaying writes after ambiguous network failures needs separate consideration.

## useful ideas in the reusable SDK

| Component | What the source provides | Implication for Semble |
|---|---|---|
| [Connector search](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/connectors/search.ts) | Separate path/method/connector/description weights; camelCase normalization; exact/prefix boosts; query coverage; structured score/total/truncated output | A candidate ranking design, not demonstrated superiority. Long conversational queries may miss coverage thresholds. It does not index arbitrary nested schema fields. |
| [Targeted describe](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/connectors/describe.ts) and [type rendering](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/json-schema-types.ts) | Method-level or connector-level declarations, field documentation, enums, requiredness and nested types derived from JSON Schema | Strong precedent for a useful middle ground between `object[]` and the full schema dump. Keep JSON Schema as the source; Python execution need not expose TypeScript syntax. |
| [Executor](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/executor.ts) and [runCode](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/run-code.ts) | Capture console logs separately from results; include logs with execution errors in this helper path | A possible result/diagnostics separation. Do not infer every SDK MCP adapter exposes logs: the inspected OpenAPI handler primarily renders the result. Any Semble logging would need bounded output and a distinction from the answer. |
| [Structured truncation](https://github.com/cloudflare/agents/blob/43a58a1014fbe6f1fe3a1fcc38ad08d53bb5b112/packages/codemode/src/truncate.ts) | `truncateResult` preserves valid JSON while marking omitted values; distinct from the text-slicing helper | Better than malformed JSON, but omission markers can change array element types or object schemas. Valid JSON is not a complete or schema-valid answer. Apply output limits after sandbox computation, not to data the computation still needs. |

The SDK ranker requires all query tokens for queries up to two tokens and 60% for longer ones, unless an exact phrase matches. Those thresholds are heuristics. Our recorded searches contain conversational filler and our catalog lacks descriptions on 47 of 51 methods, so adopting the thresholds without evidence would be premature.

## direct discovery observations

Direct calls are exploratory, hand-written searches against different APIs, not a head-to-head performance benchmark. Inputs and complete returned MCP messages are saved in [the discovery capture directory](../evals/results/discovery-study-2026-09-12/). These local captures are ignored by git; this document records the material findings.

Semble, using `search` with `detail=brief` and `limit=10`:

| Query | Observed result |
|---|---|
| `collections_get` | The exactly named tool ranked seventh, below several other collection and graph operations. |
| `get collection items` | `collections_get` ranked seventh; follower-count and contributor/follower operations ranked ahead of it. |
| `get collection items`, restricted to the `collections` tag | `collections_get` moved to fourth. Filtering helps but does not repair ranking by itself. |
| `library save count url` | `cards_get_libraries_for_url` was absent from the top ten. Library-status and mutation tools appeared first; `cards_get_url_metadata` appeared ninth. |
| `libraries`, restricted to the `cards` tag | Exactly one result: `cards_get_libraries_for_url`. |

These observations support specific candidate changes: exact identifier precedence, exposing the existing domain tags, and descriptions that connect user vocabulary to method semantics. Singular/plural normalization is worth considering, but these queries alone do not isolate its effect from descriptions, field weighting, or token coverage.

Cloudflare:

1. Filtering GET operations whose paths contain `workers/scripts` returned 16 endpoint summaries in 2,458 characters. This includes related deployments/settings/versions, so code search does not choose the intended operation for the model automatically.
2. Selecting List Workers parameters plus its entire response schema returned truncated text: 24,114 characters including the truncation notice; the server estimated the uncut result at about 13,145 tokens. The returned schema also contained `$circular` placeholders, so “pre-resolved” must not be treated as a guarantee of a fully expanded, validator-ready schema.
3. Refining the query to parameters, the names of available worker fields, and the definitions of id/created_on/modified_on/tags returned 2,197 characters without truncation. Useful descriptions and constraints were retained for those selected fields. This was a targeted view, not a complete schema replacement.

The observation is that projection can recover a useful small result after an oversized one. It is not evidence that these hand-written queries are easier for every model than our search API, or that Cloudflare is immune to schema bloat. Returning a complete resolved schema remains expensive there too.

## ideas that fit our scale

**First: a compact domain map and meaningful method contracts.** Cloudflare gives product orientation before search. Semble already tags eight SDK resource groups. FastMCP's existing `GetTags` and `ListTools` factories can support explicit browsing; a short domain map could also live in a tool description. This is especially plausible with 51 tools, where exhaustive names are tractable. These alternatives have different upfront costs; this study does not choose one or claim a measured benefit.

**Second: targeted schema disclosure.** Let a caller inspect parameters or the particular output subtree it needs, with requiredness, enums, nullability and field descriptions intact. Our observed comparison needs URL, global library-save count and pagination semantics, not every nested author and connection model. The owner is a custom discovery renderer/factory fed by the actual catalog, plus SDK annotations for missing semantics. Avoid maintaining a second handcrafted schema catalog or hardcoding the benchmark's winner/task.

**Third: teach the execution contract with one small, general example.** Show fetching data, selecting fields or aggregating, and returning the compact result in one block. Explicitly state fresh scope and supported output behavior. FastMCP already exposes `execute_description`; this does not require a sandbox replacement. Explain that library saves and collection membership are different measures in the owning method/model documentation.

**Fourth: explicit completeness and recovery.** Oversized output, unknown tools, invalid parameters and missing return values should leave the model a clear next step. A missing return can be legitimate for a write operation, so an empty-output diagnostic must not declare every such call a failure. Preserve observed errors; do not invent unavailable fields or silently turn truncated results into complete ones.

**Exact identifier lookup has direct evidence; broader ranking and programmable search remain alternatives, not predetermined changes.** `Search(search_fn=...)` can replace ranking; `CodeMode(discovery_tools=...)` permits a new discovery interface over the auth-filtered catalog. Any executable discovery must retain sandbox isolation and omit the API-calling callback. We do not need JavaScript or an OpenAPI conversion to select fields from a JSON-compatible tool catalog.

## machinery to leave aside

- Cloudflare-specific Worker loaders, R2 spec storage, scheduled spec refresh and multi-account OAuth. Semble has a small reflected catalog and a working Horizon deployment.
- Persistent execution sessions. Cloudflare production uses fresh isolates too, and persistence introduces lifecycle/isolation concerns beyond our current discovery problem.
- A wholesale move from SDK method calls to arbitrary HTTP requests. Our host callback already owns authentication, validation and dispatch.
- Embedding/vector search. The inspected relevant Cloudflare implementations do not establish a need for it here.
- Blind schema inlining or truncation as a size fix. Projection and documentation address understanding; omission can compromise correctness.

One local efficiency detail deserves separate attention later: the authenticated Semble wrapper creates and closes a client for every nested tool call. Source inspection suggests potential connection-reuse overhead, but the current traces do not isolate its cost. Do not let that hypothesis displace the documented discovery and execution-contract issues.

## outcome and remaining uncertainty

We have source-backed options and existing extension points, not evidence that an alternative will improve model performance. The highest-confidence opportunities are exact identifier precedence, richer semantic contracts, useful targeted schema views, and clearer execution guidance. A compact browse path may suit our scale better than increasingly sophisticated search alone. Ranking changes, programmable discovery, logging and output limits each need an explicit contract before implementation.

This completes the research goal. Further evaluations remain out of scope. The next decision is which narrow design to propose for Semble, keeping the existing FastMCP/Monty/Horizon foundation unless a concrete API gap requires more.
