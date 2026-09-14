import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";
import { judgeAnswer } from "./judge.js";

const collectionIds = [
  "ca9cbf0b-fc76-43e5-a676-05a7262b08a9",
  "21d2b63c-2131-412a-b9b8-13aa6f6637d7",
];

export const collectionPrompt = `Compare Semble collections ${collectionIds[0]} and ${collectionIds[1]}.
Among the URLs present in BOTH collections, find the one saved in the
most libraries across Semble. If several tie for the highest count,
return any one of them. Identify the URL and its library save count.
If the collections share no URLs, say so.
Use current data and make only read-only calls.`;

const collectionPage = z.object({
  id: z.string(), urlCards: z.array(z.object({ id: z.string(), url: z.string() })),
  pagination: z.object({
    currentPage: z.number().int(), totalCount: z.number().int().nonnegative(), hasMore: z.boolean(),
  }),
});
const metadata = z.object({ stats: z.object({ libraryCount: z.number().int().nonnegative() }) });

export interface CollectionEvidence {
  collections: { id: string; urls: string[] }[];
  counts: { url: string; saveCount: number }[];
}

export function compareCollectionEvidence(before: CollectionEvidence, after: CollectionEvidence) {
  if (JSON.stringify(before) !== JSON.stringify(after)) {
    return { verdict: "inconclusive", reason: "Collection membership or save counts changed" };
  }
  const maximum = before.counts.length ? Math.max(...before.counts.map((entry) => entry.saveCount)) : null;
  const winners = before.counts.filter((entry) => entry.saveCount === maximum).map((entry) => entry.url);
  return {
    verdict: "stable", reason: "Live observations agree",
    maximum, winners, overlapSize: before.counts.length, emptyOverlap: before.counts.length === 0,
  };
}

export function collectionRunGrade(status: Awaited<ReturnType<typeof runEval>>,
  before?: CollectionEvidence, after?: CollectionEvidence) {
  if (status !== "completed") {
    return { verdict: "fail", reason: `Agent failed to complete: ${status}`, failureKind: "execution" };
  }
  if (!before || !after) return { verdict: "inconclusive", reason: "Checker could not obtain complete evidence" };
  return compareCollectionEvidence(before, after);
}

async function observeCollections(apiKey: string, path: string) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const requests: { endpoint: string; params: Record<string, string>; status: number; body: z.infer<ReturnType<typeof z.json>>; at: string }[] = [];
  const signal = AbortSignal.timeout(60_000);
  async function get(endpoint: string, params: Record<string, string>) {
    const url = new URL(`https://api.semble.so/xrpc/${endpoint}`);
    url.search = new URLSearchParams(params).toString();
    const response = await fetch(url, { headers: { "X-API-Key": apiKey }, signal });
    const body = z.json().parse(await response.json());
    requests.push({ endpoint, params, status: response.status, body, at: new Date().toISOString() });
    if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
    return body;
  }
  try {
    const evidence: CollectionEvidence = { collections: [], counts: [] };
    for (const id of collectionIds) {
      const urls = new Set<string>();
      const cards = new Set<string>();
      let total: number | undefined;
      for (let page = 1; ; page++) {
        if (page > 100) throw new Error("Collection pagination exceeded checker limit");
        const response = collectionPage.parse(await get("network.cosmik.collection.get", {
          collectionId: id, page: String(page), limit: "50", sortBy: "createdAt", sortOrder: "asc",
        }));
        if (response.id !== id || response.pagination.currentPage !== page) throw new Error("Unexpected collection page");
        total ??= response.pagination.totalCount;
        if (total !== response.pagination.totalCount) throw new Error("Collection count changed during pagination");
        for (const card of response.urlCards) {
          if (cards.has(card.id)) throw new Error("Repeated card during pagination");
          cards.add(card.id);
          urls.add(card.url);
        }
        if (!response.pagination.hasMore) {
          if (cards.size !== total) throw new Error("Incomplete collection enumeration");
          break;
        }
        if (!response.urlCards.length) throw new Error("Empty page with hasMore=true");
      }
      evidence.collections.push({ id, urls: [...urls].sort() });
    }
    const [a, b] = evidence.collections;
    if (!a || !b) throw new Error("Missing collection evidence");
    const shared = a.urls.filter((url) => b.urls.includes(url));
    for (const url of shared) {
      const response = metadata.parse(await get("network.cosmik.card.getUrlMetadata", { url, includeStats: "true" }));
      evidence.counts.push({ url, saveCount: response.stats.libraryCount });
    }
    return { status: "ok", evidence } as const;
  } catch (error) {
    return { status: "error", error: error instanceof Error ? error.message : String(error) } as const;
  } finally {
    await writeFile(path, JSON.stringify({ startedAt, elapsedMs: Math.round(performance.now() - start), requests }, null, 2));
  }
}

export async function runCollectionTask(run: EvalRun) {
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const apiKey = variable ? process.env[variable] : undefined;
  if (!apiKey) throw new Error("Collection checker requires the server's Semble API key");
  await mkdir(run.outputDir);
  const before = await observeCollections(apiKey, join(run.outputDir, "checker-before.json"));
  const status = await runEval(run);
  const after = await observeCollections(apiKey, join(run.outputDir, "checker-after.json"));
  const result = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(run.outputDir, "result.json"), "utf8")));
  let grade = collectionRunGrade(status, before.status === "ok" ? before.evidence : undefined,
    after.status === "ok" ? after.evidence : undefined);
  if (grade.verdict === "stable") {
    try {
      const verdict = await judgeAnswer({
        task: run.prompt, answer: result.output, model: run.matrix.judge,
        runtime: run.runtime, outputDir: run.outputDir,
        rubric: "Pass if the final answer identifies any winning URL and its exact library save count. " +
          "A URL without a trailing slash is equivalent to the same root URL with a trailing slash. " +
          "Do not fail for prose, Markdown, or a code fence. Fail incorrect or missing counts, " +
          "a non-winning URL, or a contradictory final conclusion. If overlap is empty, pass an explicit " +
          "statement that no URLs are shared. Check all additional factual claims, including alleged ties, " +
          "against the full shared-URL counts. A single winning URL is not a tie merely because it occurs " +
          "in both collections. Authoritative live API expectation: " + JSON.stringify(grade) +
          " Shared URLs and library save counts: " + JSON.stringify(before.status === "ok" ? before.evidence.counts : []),
      });
      grade = { ...grade, verdict: verdict.evidenceSufficient === false ? "inconclusive" : verdict.passed ? "pass" : "fail", reason: verdict.reason };
    } catch (error) {
      grade = { ...grade, verdict: "inconclusive", reason: `Judge failed: ${error instanceof Error ? error.message : String(error)}` };
    }
  }
  await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({ gradingVersion: 2, task: "collection-overlap-popularity", executionStatus: status, ...grade, before, after }, null, 2));
  return grade.verdict;
}
