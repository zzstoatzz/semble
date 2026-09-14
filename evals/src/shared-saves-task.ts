import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";

export const sharedSavers = [
  "hyl.st", "zafarali.me", "aaronstevenwhite.io", "finest.day", "tgoerke.bsky.social", "blue-phia.bsky.social",
] as const;

export const sharedSavesPrompt = `I follow these people on Semble: ${sharedSavers.join(", ")}.
I'm curious what they have in common. Which links have more than one of
them saved, and who saved each one? List every such link with the handles
of the people who saved it. Use current data and make only read-only calls.`;

const cardsPage = z.object({
  cards: z.array(z.object({ id: z.string(), url: z.string() })),
  pagination: z.object({ currentPage: z.number().int(), totalCount: z.number().int().nonnegative(), hasMore: z.boolean() }),
});

export interface SharedSavesEvidence {
  libraries: { handle: string; urls: string[] }[];
  shared: { url: string; savers: string[] }[];
}

/** A trailing slash is the only tolerated spelling difference between the API and an answer. */
export function canonicalUrl(url: string) {
  return url.replace(/\/+$/, "");
}

export function sharedFromLibraries(libraries: SharedSavesEvidence["libraries"]) {
  const savers = new Map<string, Set<string>>();
  for (const library of libraries) {
    for (const url of new Set(library.urls.map(canonicalUrl))) {
      const set = savers.get(url) ?? new Set<string>();
      set.add(library.handle);
      savers.set(url, set);
    }
  }
  return [...savers].filter(([, set]) => set.size >= 2)
    .map(([url, set]) => ({ url, savers: [...set].sort() }))
    .sort((a, b) => a.url.localeCompare(b.url));
}

function occurrences(text: string, url: string) {
  const positions: number[] = [];
  for (const variant of new Set([url, `${url}/`])) {
    let index = text.indexOf(variant);
    while (index !== -1) {
      const end = index + variant.length;
      // `${url}/` must not count `${url}/more`; a bare url must not count a longer url sharing its prefix.
      const next = text[end];
      if (next === undefined || !/[A-Za-z0-9._~:/?#[\]@!$&'()*+,;=%-]/.test(next) || (variant === url && next === "/" && !/[A-Za-z0-9]/.test(text[end + 1] ?? ""))) positions.push(index);
      index = text.indexOf(variant, index + 1);
    }
  }
  return [...new Set(positions)].sort((a, b) => a - b);
}

/**
 * Deterministic grade: every shared URL appears, no unshared library URL appears, and
 * the passage following each shared URL names exactly its savers among the six handles.
 */
export function gradeSharedSaves(answer: string, evidence: SharedSavesEvidence) {
  const expected = sharedFromLibraries(evidence.libraries);
  const text = answer;
  const anchors = expected.flatMap((entry) => occurrences(text, entry.url).map((at) => ({ at, entry })));
  anchors.sort((a, b) => a.at - b.at);
  const missing = expected.filter((entry) => !occurrences(text, entry.url).length).map((entry) => entry.url);
  if (missing.length) return { verdict: "fail", reason: `Answer omits ${missing.length} of ${expected.length} shared links`, missing };
  const sharedSet = new Set(expected.map((entry) => entry.url));
  const unshared = new Set(evidence.libraries.flatMap((library) => library.urls.map(canonicalUrl)).filter((url) => !sharedSet.has(url)));
  const falsePositives = [...unshared].filter((url) => occurrences(text, url).length);
  if (falsePositives.length) return { verdict: "fail", reason: `Answer lists ${falsePositives.length} links saved by only one person`, falsePositives };
  const misattributed: { url: string; expected: string[]; found: string[] }[] = [];
  for (const [index, anchor] of anchors.entries()) {
    const end = anchors[index + 1]?.at ?? text.length;
    const passage = text.slice(anchor.at, end);
    const found = sharedSavers.filter((handle) => passage.includes(handle)).sort();
    if (JSON.stringify(found) !== JSON.stringify(anchor.entry.savers)) misattributed.push({ url: anchor.entry.url, expected: anchor.entry.savers, found });
  }
  if (misattributed.length) return { verdict: "fail", reason: `Answer misattributes savers for ${misattributed.length} links`, misattributed };
  return { verdict: "pass", reason: `All ${expected.length} shared links listed with correct savers and no extras` };
}

export function sharedSavesRunGrade(status: Awaited<ReturnType<typeof runEval>>, answer: string,
  before?: SharedSavesEvidence, after?: SharedSavesEvidence) {
  if (status !== "completed") return { verdict: "fail", reason: `Agent failed to complete: ${status}`, failureKind: "execution" };
  if (!before || !after) return { verdict: "inconclusive", reason: "Checker could not obtain complete evidence" };
  if (JSON.stringify(sharedFromLibraries(before.libraries)) !== JSON.stringify(sharedFromLibraries(after.libraries))) {
    return { verdict: "inconclusive", reason: "Shared links changed during the run" };
  }
  return gradeSharedSaves(answer, before);
}

async function observeLibraries(apiKey: string, path: string) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const requests: { endpoint: string; params: Record<string, string>; status: number; at: string }[] = [];
  const signal = AbortSignal.timeout(120_000);
  async function get(endpoint: string, params: Record<string, string>) {
    const url = new URL(`https://api.semble.so/xrpc/${endpoint}`);
    url.search = new URLSearchParams(params).toString();
    const response = await fetch(url, { headers: { "X-API-Key": apiKey }, signal });
    requests.push({ endpoint, params, status: response.status, at: new Date().toISOString() });
    if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
    return z.json().parse(await response.json());
  }
  try {
    const libraries: SharedSavesEvidence["libraries"] = [];
    for (const handle of sharedSavers) {
      const urls: string[] = [];
      const cards = new Set<string>();
      let total: number | undefined;
      for (let page = 1; ; page++) {
        if (page > 100) throw new Error("Library pagination exceeded checker limit");
        const response = cardsPage.parse(await get("network.cosmik.card.listByUser", {
          identifier: handle, page: String(page), limit: "100", sortBy: "createdAt", sortOrder: "asc",
        }));
        if (response.pagination.currentPage !== page) throw new Error("Unexpected library page");
        total ??= response.pagination.totalCount;
        if (total !== response.pagination.totalCount) throw new Error("Library count changed during pagination");
        for (const card of response.cards) {
          if (cards.has(card.id)) throw new Error("Repeated card during pagination");
          cards.add(card.id);
          urls.push(card.url);
        }
        if (!response.pagination.hasMore) {
          if (cards.size !== total) throw new Error("Incomplete library enumeration");
          break;
        }
        if (!response.cards.length) throw new Error("Empty page with hasMore=true");
      }
      libraries.push({ handle, urls: urls.sort() });
    }
    return { status: "ok", evidence: { libraries, shared: sharedFromLibraries(libraries) } } as const;
  } catch (error) {
    return { status: "error", error: error instanceof Error ? error.message : String(error) } as const;
  } finally {
    await writeFile(path, JSON.stringify({ startedAt, elapsedMs: Math.round(performance.now() - start), requests }, null, 2));
  }
}

export async function runSharedSavesTask(run: EvalRun) {
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const apiKey = variable ? process.env[variable] : undefined;
  if (!apiKey) throw new Error("Shared-saves checker requires the server's Semble API key");
  await mkdir(run.outputDir);
  const before = await observeLibraries(apiKey, join(run.outputDir, "checker-before.json"));
  const status = await runEval(run);
  const after = await observeLibraries(apiKey, join(run.outputDir, "checker-after.json"));
  const result = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(run.outputDir, "result.json"), "utf8")));
  const grade = sharedSavesRunGrade(status, result.output, before.status === "ok" ? before.evidence : undefined,
    after.status === "ok" ? after.evidence : undefined);
  await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({
    gradingVersion: 1, task: { name: "shared-saves", kind: "shared-saves" }, executionStatus: status, ...grade,
    expected: before.status === "ok" ? before.evidence.shared : null,
    before: before.status === "ok" ? { libraries: before.evidence.libraries.map((library) => ({ handle: library.handle, count: library.urls.length })) } : before,
    after: after.status === "ok" ? { libraries: after.evidence.libraries.map((library) => ({ handle: library.handle, count: library.urls.length })) } : after,
  }, null, 2));
  return grade.verdict;
}
