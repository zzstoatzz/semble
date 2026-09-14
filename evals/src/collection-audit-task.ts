import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";
import { canonicalUrl, urlOccurrences } from "./shared-saves-task.js";

export const auditIdentifier = "joe.germuska.com";

export const collectionAuditPrompt = `I'm helping ${auditIdentifier} tidy up their Semble library. Which of their collections are empty or hold only a single card, and which of their saved links aren't in any collection yet? List the collection names and the uncollected links. Don't change anything.`;

const pagination = z.object({ currentPage: z.number().int(), totalCount: z.number().int().nonnegative(), hasMore: z.boolean() });
const collectionsPage = z.object({ collections: z.array(z.object({ id: z.string(), name: z.string(), cardCount: z.number().int().nonnegative() })), pagination });
const cardsPage = z.object({ cards: z.array(z.object({ id: z.string(), url: z.string() })), pagination });

export interface CollectionAuditEvidence {
  sparseCollections: { name: string; cardCount: number }[];
  uncollectedUrls: string[];
}

function mentions(text: string, needle: string) {
  return text.toLowerCase().includes(needle.toLowerCase());
}

/** Every sparse collection name and every uncollected link must appear in the answer. */
export function gradeCollectionAudit(answer: string, evidence: CollectionAuditEvidence) {
  const missingCollections = evidence.sparseCollections.filter((collection) => !mentions(answer, collection.name)).map((collection) => collection.name);
  const missingUrls = evidence.uncollectedUrls.filter((url) => !urlOccurrences(answer, canonicalUrl(url)).length);
  if (missingCollections.length || missingUrls.length) {
    const parts = [];
    if (missingCollections.length) parts.push(`${missingCollections.length} of ${evidence.sparseCollections.length} sparse collections`);
    if (missingUrls.length) parts.push(`${missingUrls.length} of ${evidence.uncollectedUrls.length} uncollected links`);
    return { verdict: "fail", reason: `Answer omits ${parts.join(" and ")}`, missing: { collections: missingCollections, urls: missingUrls } };
  }
  return { verdict: "pass", reason: `All ${evidence.sparseCollections.length} sparse collections and ${evidence.uncollectedUrls.length} uncollected links listed` };
}

export function collectionAuditRunGrade(status: Awaited<ReturnType<typeof runEval>>, answer: string, before?: CollectionAuditEvidence, after?: CollectionAuditEvidence) {
  if (status !== "completed") return { verdict: "fail", reason: `Agent failed to complete: ${status}`, failureKind: "execution" };
  if (!before || !after) return { verdict: "inconclusive", reason: "Checker could not obtain complete evidence" };
  if (JSON.stringify(before) !== JSON.stringify(after)) return { verdict: "inconclusive", reason: "Library changed during the run" };
  return gradeCollectionAudit(answer, before);
}

async function observeAudit(apiKey: string, path: string) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const requests: { endpoint: string; params: Record<string, string>; status: number; at: string }[] = [];
  const signal = AbortSignal.timeout(90_000);
  async function get(endpoint: string, params: Record<string, string>) {
    const url = new URL(`https://api.semble.so/xrpc/${endpoint}`);
    url.search = new URLSearchParams(params).toString();
    const response = await fetch(url, { headers: { "X-API-Key": apiKey }, signal });
    requests.push({ endpoint, params, status: response.status, at: new Date().toISOString() });
    if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
    return z.json().parse(await response.json());
  }
  try {
    const sparse: CollectionAuditEvidence["sparseCollections"] = [];
    const ids = new Set<string>();
    for (let p = 1; ; p++) {
      if (p > 20) throw new Error("collection pagination exceeded checker limit");
      const parsed = collectionsPage.parse(await get("network.cosmik.collection.listByUser", { identifier: auditIdentifier, page: String(p), limit: "100" }));
      if (parsed.pagination.currentPage !== p) throw new Error("unexpected collection page");
      for (const collection of parsed.collections) {
        if (ids.has(collection.id)) throw new Error("repeated collection during pagination");
        ids.add(collection.id);
        if (collection.cardCount <= 1) sparse.push({ name: collection.name, cardCount: collection.cardCount });
      }
      if (!parsed.pagination.hasMore) {
        if (ids.size !== parsed.pagination.totalCount) throw new Error("incomplete collection enumeration");
        break;
      }
      if (!parsed.collections.length) throw new Error("empty collection page with hasMore");
    }
    const uncollected: string[] = [];
    const cardIds = new Set<string>();
    for (let p = 1; ; p++) {
      if (p > 20) throw new Error("card pagination exceeded checker limit");
      const parsed = cardsPage.parse(await get("network.cosmik.card.listByUser", { identifier: auditIdentifier, uncollected: "true", page: String(p), limit: "100", sortBy: "createdAt", sortOrder: "asc" }));
      if (parsed.pagination.currentPage !== p) throw new Error("unexpected card page");
      for (const card of parsed.cards) {
        if (cardIds.has(card.id)) throw new Error("repeated card during pagination");
        cardIds.add(card.id);
        uncollected.push(card.url);
      }
      if (!parsed.pagination.hasMore) {
        if (cardIds.size !== parsed.pagination.totalCount) throw new Error("incomplete card enumeration");
        break;
      }
      if (!parsed.cards.length) throw new Error("empty card page with hasMore");
    }
    sparse.sort((a, b) => a.name.localeCompare(b.name));
    uncollected.sort();
    return { status: "ok", evidence: { sparseCollections: sparse, uncollectedUrls: uncollected } satisfies CollectionAuditEvidence } as const;
  } catch (error) {
    return { status: "error", error: error instanceof Error ? error.message : String(error) } as const;
  } finally {
    await writeFile(path, JSON.stringify({ startedAt, elapsedMs: Math.round(performance.now() - start), requests }, null, 2));
  }
}

export async function runCollectionAuditTask(run: EvalRun) {
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const apiKey = variable ? process.env[variable] : undefined;
  if (!apiKey) throw new Error("Collection-audit checker requires the server's Semble API key");
  await mkdir(run.outputDir);
  const before = await observeAudit(apiKey, join(run.outputDir, "checker-before.json"));
  const status = await runEval(run);
  const after = await observeAudit(apiKey, join(run.outputDir, "checker-after.json"));
  const result = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(run.outputDir, "result.json"), "utf8")));
  const grade = collectionAuditRunGrade(status, result.output, before.status === "ok" ? before.evidence : undefined, after.status === "ok" ? after.evidence : undefined);
  await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({
    gradingVersion: 1, task: { name: "collection-audit", kind: "collection-audit" }, executionStatus: status, ...grade,
    expected: before.status === "ok" ? before.evidence : before, after: after.status === "ok" ? "same" : after,
  }, null, 2));
  return grade.verdict;
}
