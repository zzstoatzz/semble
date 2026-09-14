import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";
import { checkCurationPage } from "./curation-task.js";

const pagination = z.object({ currentPage: z.number().int(), totalCount: z.number().int(), hasMore: z.boolean() });
const mergeCard = z.object({ id: z.string(), url: z.url(), cardContent: z.json(),
  note: z.object({ id: z.string(), text: z.string() }).nullish(),
  collections: z.array(z.object({ id: z.string() })) });
const mergeShelf = z.object({ id: z.string(), name: z.string(), description: z.string().nullish(), accessType: z.string().optional() });
const mergeCollection = mergeShelf.extend({ urlCards: z.array(z.object({ id: z.string(), url: z.url() })), pagination });
export type MergeCard = z.infer<typeof mergeCard>;
export type MergeCollection = Omit<z.infer<typeof mergeCollection>, "pagination">;
export const mergeTaskPrompt = "Combine the two supplied Semble collections into a new collection, preserving both originals and existing cards and notes.";

export function selectMergeCards(cards: MergeCard[]) {
  const selected = cards.toSorted((a, b) => a.id.localeCompare(b.id)).slice(0, 12);
  if (selected.length < 3) throw new Error("Merge task needs at least three saved cards for overlap and an exclusive item in each source");
  const exclusive = Math.max(1, Math.floor(selected.length / 3));
  return [selected.slice(0, -exclusive), selected.slice(exclusive)] as const;
}
function collectionSignature(collection: MergeCollection) {
  return JSON.stringify({ ...collection, urlCards: collection.urlCards.toSorted((a, b) => a.id.localeCompare(b.id)) });
}
function librarySignature(cards: MergeCard[], ignored: Set<string>) {
  return JSON.stringify(cards.map((card) => ({ ...card,
    collections: card.collections.filter((shelf) => !ignored.has(shelf.id)).toSorted((a, b) => a.id.localeCompare(b.id)),
  })).sort((a, b) => a.id.localeCompare(b.id)));
}
export function gradeCollectionMerge(input: {
  executionStatus: string; before: MergeCollection[]; after: MergeCollection[];
  sources: string[]; destination?: MergeCollection; extraCollections: string[];
  libraryBefore: MergeCard[]; libraryAfter: MergeCard[];
}) {
  const fail = (reason: string) => ({ verdict: "fail", reason });
  if (input.executionStatus !== "completed") return fail(`Agent failed to complete: ${input.executionStatus}`);
  if (!input.destination) return fail("Expected new destination collection is missing");
  if (input.extraCollections.length) return fail("Agent created unexpected additional collections");
  for (const original of input.before) {
    const after = input.after.find((entry) => entry.id === original.id);
    if (!after || collectionSignature(original) !== collectionSignature(after)) return fail(`Original collection changed: ${original.id}`);
  }
  const sourceCollections = input.sources.map((id) => input.before.find((entry) => entry.id === id));
  if (sourceCollections.length !== 2 || sourceCollections.some((entry) => !entry)) throw new Error("Checker is missing source collections");
  const expected = new Map(sourceCollections.flatMap((entry) => entry?.urlCards ?? []).map((card) => [card.id, card.url]));
  const actual = input.destination.urlCards;
  if (actual.length !== expected.size || new Set(actual.map((card) => card.id)).size !== actual.length ||
    actual.some((card) => expected.get(card.id) !== card.url)) return fail("Destination is not the exact union of existing source cards");
  if (librarySignature(input.libraryBefore, new Set()) !== librarySignature(input.libraryAfter, new Set([input.destination.id]))) {
    return fail("Saved cards, content, notes, or unrelated collection memberships changed");
  }
  return { verdict: "pass", reason: `Exact union of ${expected.size} existing cards; originals, content, notes and unrelated memberships preserved` };
}

// Write cells share one account. Serialize their entire setup/actor/check/cleanup lifecycle.
let mergeQueue: Promise<unknown> = Promise.resolve();
export function runCollectionMerge(run: EvalRun) {
  const result = mergeQueue.then(() => executeCollectionMerge(run));
  mergeQueue = result.catch(() => undefined);
  return result;
}
async function executeCollectionMerge(run: EvalRun) {
  await mkdir(run.outputDir, { recursive: true });
  const prefix = `eval-merge-${randomUUID()}`;
  const destinationName = `${prefix}-merged`;
  const created = new Set<string>();
  const addedCards = new Set<string>();
  let accountBefore: MergeCard[] | undefined;
  const requests: { endpoint: string; method: string; status: number; at: string }[] = [];
  let executionStatus = "not_run";
  let grade = { verdict: "inconclusive", reason: "Preflight not completed" };
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const key = variable ? process.env[variable] : undefined;
  async function api(endpoint: string, params: Record<string, string> = {}, body?: z.infer<ReturnType<typeof z.json>>) {
    const url = new URL(`https://api.semble.so/xrpc/network.cosmik.${endpoint}`);
    url.search = new URLSearchParams(params).toString();
    const method = body === undefined ? "GET" : "POST";
    const response = await fetch(url, { method, headers: { "X-API-Key": key ?? "", "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body), signal: AbortSignal.timeout(20_000) });
    requests.push({ endpoint, method, status: response.status, at: new Date().toISOString() });
    if (!response.ok) {
      const parsed = z.object({ message: z.string().optional(), error: z.string().optional() }).safeParse(await response.json());
      const message = parsed.success ? parsed.data.message ?? parsed.data.error : undefined;
      throw new Error(`${endpoint}: HTTP ${response.status}${message ? ` — ${message}` : ""}`);
    }
    const text = await response.text();
    return text ? z.json().parse(JSON.parse(text)) : null;
  }
  async function library() {
    const cards: MergeCard[] = [], state = { ids: new Set<string>() };
    for (let page = 1; page <= 10; page++) {
      const parsed = z.object({ cards: z.array(mergeCard), pagination }).parse(await api("card.listMine", { page: String(page), limit: "100" }));
      checkCurationPage(state, page, parsed.pagination, parsed.cards.map((card) => card.id));
      cards.push(...parsed.cards);
      if (!parsed.pagination.hasMore) return cards;
    }
    throw new Error("Library exceeds checker budget");
  }
  async function shelves() {
    const result: z.infer<typeof mergeShelf>[] = [], state = { ids: new Set<string>() };
    for (let page = 1; page <= 3; page++) {
      const parsed = z.object({ collections: z.array(mergeShelf), pagination }).parse(await api("collection.listMine", { page: String(page), limit: "100" }));
      checkCurationPage(state, page, parsed.pagination, parsed.collections.map((entry) => entry.id));
      result.push(...parsed.collections);
      if (!parsed.pagination.hasMore) return result;
    }
    throw new Error("Collections exceed checker budget");
  }
  async function collection(id: string): Promise<MergeCollection> {
    const cards: MergeCollection["urlCards"] = [], state = { ids: new Set<string>() };
    for (let page = 1; page <= 10; page++) {
      const parsed = mergeCollection.parse(await api("collection.get", { collectionId: id, page: String(page), limit: "100" }));
      if (parsed.id !== id) throw new Error("Collection identity mismatch");
      checkCurationPage(state, page, parsed.pagination, parsed.urlCards.map((entry) => entry.id));
      cards.push(...parsed.urlCards);
      if (!parsed.pagination.hasMore) {
        const { pagination: _pagination, ...result } = parsed;
        return { ...result, urlCards: cards };
      }
    }
    throw new Error("Collection exceeds checker budget");
  }
  try {
    if (!key) throw new Error("Missing Semble credential");
    const expected = process.env.SEMBLE_EVAL_HANDLE;
    if (!expected) throw new Error("Set SEMBLE_EVAL_HANDLE to the explicitly designated test account before running write evals");
    const profile = z.object({ id: z.string(), handle: z.string() }).parse(await api("actor.getMyProfile"));
    if (profile.handle !== expected) throw new Error("Semble credential does not match SEMBLE_EVAL_HANDLE");
    accountBefore = await library();
    await writeFile(join(run.outputDir, "account-before.json"), JSON.stringify(accountBefore, null, 2));
    // Sample real public saves to make a useful small fixture even on a new test account.
    // This is live data setup, not a mocked actor API or a fixed expected answer.
    const needed = Math.max(0, 8 - accountBefore.length);
    if (needed) {
      const source = z.object({ cards: z.array(z.object({ url: z.url() })) }).parse(await api("card.listByUser", {
        identifier: "zzstoatzz.io", limit: "100", page: "1", sortBy: "createdAt", sortOrder: "asc",
      }));
      const urls = [...new Set(source.cards.map((card) => card.url))].filter((url) => !accountBefore?.some((card) => card.url === url)).slice(0, needed);
      if (urls.length !== needed) throw new Error("Public seed library is too small; update the seed identifier");
      await writeFile(join(run.outputDir, "seed.json"), JSON.stringify({ identifier: "zzstoatzz.io", urls, addedCards: [] }, null, 2));
      for (const url of urls) {
        const added = z.object({ urlCardId: z.string() }).parse(await api("card.addUrl", {}, { url }));
        addedCards.add(added.urlCardId);
        await writeFile(join(run.outputDir, "seed.json"), JSON.stringify({ identifier: "zzstoatzz.io", urls, addedCards: [...addedCards] }, null, 2));
      }
    }
    const baseline = await library();
    const groups = selectMergeCards(baseline);
    const originalShelves = await shelves();
    if (originalShelves.length > 20) throw new Error("Use a small isolated test account (at most 20 collections)");
    const sources = [];
    for (const [index, cards] of groups.entries()) {
      const result = z.object({ collectionId: z.string() }).parse(await api("collection.create", {}, {
        name: `${prefix}-${index === 0 ? "a" : "b"}`, description: "Temporary Semble merge evaluation source", accessType: "CLOSED",
      }));
      created.add(result.collectionId);
      sources.push(result.collectionId);
      // Persist IDs before further writes, including for recovery after process interruption.
      await writeFile(join(run.outputDir, "fixture.json"), JSON.stringify({ profile, prefix, destinationName, created: [...created], groups }, null, 2));
      for (const card of cards) await api("card.updateUrlAssociations", {}, { cardId: card.id, addToCollections: [result.collectionId] });
    }
    const before = await Promise.all([...originalShelves.map((entry) => entry.id), ...sources].map(collection));
    const libraryBefore = await library();
    await writeFile(join(run.outputDir, "checker-before.json"), JSON.stringify({ before, libraryBefore, sources }, null, 2));
    const prompt = `Combine Semble collections ${sources.join(" and ")} into a new collection named "${destinationName}". Keep both originals intact, reuse the existing cards, and preserve their notes. Leave everything else in my library unchanged. Give me a link to the result.`;
    executionStatus = await runEval({ ...run, prompt });
    const observedShelves = await shelves();
    const destinations = observedShelves.filter((entry) => entry.name === destinationName && !before.some((old) => old.id === entry.id));
    const after = await Promise.all(observedShelves.map((entry) => collection(entry.id)));
    const libraryAfter = await library();
    grade = gradeCollectionMerge({ executionStatus, before, after, sources,
      destination: destinations.length === 1 ? after.find((entry) => entry.id === destinations[0]?.id) : undefined,
      extraCollections: observedShelves.filter((entry) => !before.some((old) => old.id === entry.id) && entry.name !== destinationName).map((entry) => entry.id),
      libraryBefore, libraryAfter });
    await writeFile(join(run.outputDir, "checker-after.json"), JSON.stringify({ after, libraryAfter, destinations }, null, 2));
  } catch (error) {
    grade = { verdict: executionStatus !== "not_run" && executionStatus !== "completed" ? "fail" : "inconclusive",
      reason: error instanceof Error ? error.message : String(error) };
  } finally {
    const cleanupErrors: string[] = [];
    if (created.size) {
      try {
        for (const shelf of await shelves()) if (shelf.name.startsWith(prefix)) created.add(shelf.id);
        for (const id of created) {
          try {
            const current = await collection(id);
            for (const card of current.urlCards) await api("card.updateUrlAssociations", {}, { cardId: card.id, removeFromCollections: [id] });
            await api("collection.delete", {}, { collectionId: id });
          } catch (error) { cleanupErrors.push(`${id}: ${error instanceof Error ? error.message : String(error)}`); }
        }
        const remaining = (await shelves()).filter((entry) => created.has(entry.id));
        if (remaining.length) cleanupErrors.push(`Collections remain: ${remaining.map((entry) => entry.id).join(", ")}`);
      } catch (error) { cleanupErrors.push(error instanceof Error ? error.message : String(error)); }
    }
    for (const cardId of addedCards) {
      try { await api("card.removeFromLibrary", {}, { cardId }); }
      catch (error) { cleanupErrors.push(`${cardId}: ${error instanceof Error ? error.message : String(error)}`); }
    }
    if (accountBefore) {
      try {
        const restored = await library();
        await writeFile(join(run.outputDir, "account-after.json"), JSON.stringify(restored, null, 2));
        if (librarySignature(accountBefore, new Set()) !== librarySignature(restored, new Set())) cleanupErrors.push("Account library was not restored exactly");
      } catch (error) { cleanupErrors.push(error instanceof Error ? error.message : String(error)); }
    }
    await writeFile(join(run.outputDir, "cleanup.json"), JSON.stringify({ created: [...created], addedCards: [...addedCards], errors: cleanupErrors }, null, 2));
    await writeFile(join(run.outputDir, "checker-requests.json"), JSON.stringify(requests, null, 2));
    if (cleanupErrors.length && grade.verdict === "pass") grade = { verdict: "inconclusive", reason: "Task passed but fixture cleanup failed; inspect cleanup.json" };
    await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({ gradingVersion: 1, task: { name: "collection-merge" },
      gradingMethod: "live-api-state", model: run.model.name, server: run.server.name, executionStatus, ...grade }, null, 2));
  }
  return grade.verdict;
}
