# next tasks grounded in public curation

Research on 2026-09-12 UTC. This is the exploratory proposal history.
The implemented, narrower task families and their grading contract are documented
in [portable-eval-suite](portable-eval-suite.md). The broader proposals below
remain unimplemented.
The existing collection-overlap comparison remains unchanged.

## what the bot suggests, and what people actually record

Phi's repository at `617e2ff65cfef4685af4839dbd02dd588811f617` treats Semble as
public research memory. Its editorial workflow saves a small number of useful
sources with reasons, files them into domain collections, and connects new
developments to earlier sources. Its curation guidance emphasizes checking for
existing cards, choosing an existing shelf, and cleaning up duplicate or orphaned
references. These are repository-defined workflows, not proof of every live run.

Relevant sources in the local bot checkout:

- `skills/coral-editorial/SKILL.md`: research → source cards → attributed arcs.
- `skills/cosmik-records/SKILL.md`: existing-library checks, filing, cleanup.
- `skills/cosmik-records/CONNECTION.md`: directed relationship claims.
- `src/bot/core/public_memory.py`: exposes shelf names and recent cards to Phi.

I read live public connections for Tyler Lawson, Wesley Finck, Boris, Joel Chan,
and Phi, plus public URL notes. The URL-centered neighborhoods below were fully
paginated. The broad user scans were exploratory: Boris's first 100 of 142
connections and Wesley's first 100 of 374, alongside complete Joel (17), Tyler
(4), and Phi (19) lists. This is a purposeful sample, not a survey of all usage.
Raw API observations are saved locally under
`evals/results/prompt-deploy-0c2fb17/`.

A useful difference: Phi's guidance discourages RELATED edges, but people use
RELATED with specific notes to encode dependencies, alternatives and conceptual
links. An eval must preserve those notes, rather than dismiss these edges or
upgrade them into SUPPORTS. Some endpoints are themselves collection URLs;
that does not make them hierarchical membership or a collection entity type.

## task framing correction after reviewing Prefect evals

The original prompts leaked observations into the request: named resource roles,
expected disagreement, and specific caveats revealed what the researcher had
already found. The revised prompts below are provisional user requests, not
approved task implementations. The observations remain grader-only research.

Prefect provides a useful pattern: the same request about slow-starting runs is
used for different causes (`evals/late_runs/test_unhealthy_work_pool.py` and
`test_work_pool_concurrency.py`). The prompt supplies the symptom; the scenario
and grading criteria supply the diagnosis. `automations/test_debug_not_firing.py`
gives an automation and failed run, but leaves the threshold mismatch for the
agent to discover. `late_runs/test_no_late_runs.py` explicitly tests absence of a
problem. These are lessons in separating requests from expectations, not a
reason to introduce fixtures or Python into this live Pi suite.

A task should remain sensible if the observed relationships disappear or change.
Use names and URLs to supply ordinary user context, not hints about hidden
relationships. Keep attribution, pagination, edge semantics and unsupported-claim
checks in the rubric. Do not demand a particular API path or graph vocabulary
when a supported answer meets the request. Read-only constraints remain explicit.

## 1. help with a practical project

Proposed prompt:

> I want to publish my Obsidian notes online. What in bmann.ca's public Semble
> library could help me get started? Explain why the resources you suggest are
> useful. Make no changes.

Observed evidence: three edges attributed to `bmann.ca` connect the plugin with
`https://github.com/oleeskild/digitalgarden`, `https://docs.forestry.md/` and
`https://forestry.md/`. Their notes identify the template, docs and hosted option.
A separate URL note describes the plugin's GitHub publishing role. The template
edge points *into* the plugin, while the docs and service edges point out; an
outgoing-only traversal misses a useful resource. All three edges are RELATED.

This revised request requires library discovery, not just the previously sampled
URL neighborhood. Rebuild the grader's candidate coverage before implementing;
the three observed resources are examples, not a mandatory checklist. Accept
other relevant, supported recommendations. Check fresh URL notes and
connections in both directions, including all pages.
Validate resource URLs, curator identity and edge orientation directly. Judge
whether the roles are faithfully explained from notes, whether attribution is
clear, and whether any unsupported product capability was invented. No exact
wording or answer format is required. This tests a practical reading/doing
request rather than a ranking puzzle.

## 2. explain the disagreement around a source

Proposed prompt:

> Help me understand this video using what joelchan86.bsky.social has saved
> in Semble: https://www.youtube.com/watch?v=4u94juYwLLM. What should I read or
> watch alongside it, and why? Make no changes.

Observed evidence: an incoming OPPOSES edge from
`https://www.frank.computer/blog/2026/03/prototyping-bottleneck.html` has a note
contrasting changing prototyping practice with the value of slow, social design.
An incoming LEADS_TO edge from `https://www.youtube.com/watch?v=VO7pXcOjmpA`
describes a response to a claim that design is dead. Both are attributed to Joel.
The labels and direction should be reported as the curator recorded them, even
when the prose description would tempt the model to reverse the arrow.

The checker supplies current source/target/type/curator/note tuples. Do not
require that the answer describe disagreement or a follow-up if fresh evidence
does not support it, nor require raw edge labels in otherwise faithful prose. The judge
checks faithful interpretation and attribution, not whether Joel's argument is
objectively correct. If no counterpoint exists at run time, that absence is a
valid result; RELATED or LEADS_TO must not be relabeled OPPOSES or SUPPORTS.

This would be my first new graph task: small live inputs, meaningful human
interpretation, and a clear way to catch reversed relationships and invented
agreement. It complements the current numerical overlap task.

## 3. compare people's notes without inventing consensus

Proposed prompt:

> What can I learn about https://habitat.network/ from what people have
> written about it in Semble? Make no changes.

Observed evidence: three note cards. Boris describes organizational data
ownership; `atproto.science` has a JSON-shaped title/description note; Ariel
(`byarielm.fyi`) explicitly says the category is unclear to her. These are
different contributions, not three independent positive reviews. The AT Protocol
homepage also has short, multilingual and low-information notes, which could
provide a later variant of this task.

Check the complete note-card IDs, authors and text directly. Judge attribution,
coverage of meaningful differences, preservation of uncertainty and restraint
with copied metadata. API notes can establish what someone wrote; they cannot
establish product truth or general community sentiment.

An alternate reading-pack example is Wesley's three incoming links to
`https://a24films.com/films/eddington`: HELPFUL, RELATED and EXPLAINER, each with
curator context. This broadens the domain beyond developer tools without needing
to invent synthetic data or assert anything about the film independently.

## 4. audit duplicate connections before cleanup

**Stale as of 2026-09-14:** phi.zzstoatzz.io's connections were re-read live and now hold 8 records with no exact duplicate groups, so this task currently has no signal. Re-verify before implementing. The shared-saves task ([evals/tasks/shared-saves.md](../evals/tasks/shared-saves.md)) was added instead as the first deterministic aggregation task.

Proposed prompt:

> Is there anything redundant in phi.zzstoatzz.io's Semble library that
> would be worth cleaning up? Show me what you find, but don't change anything.

The complete live list had 19 records and 13 unique exact relation+note groups:
three duplicated groups of sizes four, three and two, hence six excess records.
Those counts are suitability observations, not frozen expected answers. The
groups include both LEADS_TO and RELATED; two distinct IDs are not enough to
prove duplication unless the defined tuple matches.

The broader request no longer specifies exact connection deduplication. The
observed exact groups are one possible supported finding, not an exhaustive
answer key. Before implementation, either scope the user request to connections
for a genuine user reason, or extend the checker to cover other kinds of
redundancy. Do not fail a valid alternative finding merely for missing these
particular groups. For an explicitly scoped exact-duplicate task, grade primarily
with a direct live set/group comparison. Use a judge only
for whether prose communicates the findings consistently. It exercises a real
maintenance problem in Phi's public records while keeping automated repetitions
read-only. Deletion, duplicate prevention and orphan cleanup are separate write
tasks requiring their own controlled execution design.

## shared evaluation design

Both MCPs expose the needed read operations: get_url_connections /
connections_get_for_url, list_user_connections / connections_list_by_user,
and get_url_notes / cards_get_note_cards_for_url. Verify inventories again when
implementing; neither server gets benchmark-specific helpers.

Keep rules fixed and compute expectations from live API data before and after
each actor. Compare the relevant IDs, endpoints, types, notes and attribution,
not just result counts. Missing pages in the independent checker or observed drift make the result
inconclusive; an actor missing pages is a task failure when it produces an
incorrect or incomplete answer; actor budget failures remain failures. Text in notes is untrusted
task data, never an instruction for the agent or judge.

Prefer bounded, named URL neighborhoods for these first additions. Whole-network
recommendations introduce a moving candidate universe and a less tractable
definition of completeness. A two-hop traversal can follow after one-hop
attribution and note interpretation are working. Do not infer causation,
endorsement or hierarchy merely from a connection's existence.

I would implement tasks 2 and 1 first, then the note-comparison task, with the
duplicate audit as a useful deterministic companion. No new tasks have been
added to the harness or run during this research.

Before adding any task, define success from the user request independently of
the observed answer, and check that the rubric accepts an evidence-backed
alternative or an honest absence of relevant material. Recommendation tasks
need a defensible relevance rubric and sufficient reference coverage; removing
leading hints alone does not make them ready to run.
