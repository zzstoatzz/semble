import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";

export const linkContextUrl = "https://habitat.network/";

export const linkContextPrompt = `A friend sent me ${linkContextUrl} and said "people on Semble are into this". Before I read it: who on Semble has saved it, which collections is it filed in, and what have people written about it in their notes? I want the handles, the collection names, and who wrote each note. Don't change anything.`;

const page = z.object({ pagination: z.object({ currentPage: z.number().int(), totalCount: z.number().int().nonnegative(), hasMore: z.boolean() }) });
const librariesPage = page.extend({ libraries: z.array(z.object({ user: z.object({ handle: z.string() }) })) });
const collectionsPage = page.extend({ collections: z.array(z.object({ id: z.string(), name: z.string(), author: z.object({ handle: z.string() }).optional() })) });
const notesPage = page.extend({ notes: z.array(z.object({ id: z.string(), note: z.string(), author: z.object({ handle: z.string() }) })) });

export interface LinkContextEvidence {
  savers: string[];
  collections: { name: string; owner: string | null }[];
  notes: { author: string; note: string }[];
}

function mentions(text: string, needle: string) {
  return text.toLowerCase().includes(needle.toLowerCase());
}

/** Every saver handle, collection name, and note author must appear in the answer. */
export function gradeLinkContext(answer: string, evidence: LinkContextEvidence) {
  const missingSavers = evidence.savers.filter((handle) => !mentions(answer, handle));
  const missingCollections = evidence.collections.filter((collection) => !mentions(answer, collection.name)).map((collection) => collection.name);
  const missingNoteAuthors = [...new Set(evidence.notes.map((note) => note.author))].filter((handle) => !mentions(answer, handle));
  const missing = { savers: missingSavers, collections: missingCollections, noteAuthors: missingNoteAuthors };
  const total = missingSavers.length + missingCollections.length + missingNoteAuthors.length;
  if (total) {
    const parts = [];
    if (missingSavers.length) parts.push(`${missingSavers.length} of ${evidence.savers.length} savers`);
    if (missingCollections.length) parts.push(`${missingCollections.length} of ${evidence.collections.length} collections`);
    if (missingNoteAuthors.length) parts.push(`${missingNoteAuthors.length} note authors`);
    return { verdict: "fail", reason: `Answer omits ${parts.join(", ")}`, missing };
  }
  return { verdict: "pass", reason: `All ${evidence.savers.length} savers, ${evidence.collections.length} collections and ${evidence.notes.length} note authors named` };
}

function sameContext(a: LinkContextEvidence, b: LinkContextEvidence) {
  return JSON.stringify(a) === JSON.stringify(b);
}

export function linkContextRunGrade(status: Awaited<ReturnType<typeof runEval>>, answer: string, before?: LinkContextEvidence, after?: LinkContextEvidence) {
  if (status !== "completed") return { verdict: "fail", reason: `Agent failed to complete: ${status}`, failureKind: "execution" };
  if (!before || !after) return { verdict: "inconclusive", reason: "Checker could not obtain complete evidence" };
  if (!sameContext(before, after)) return { verdict: "inconclusive", reason: "Link context changed during the run" };
  return gradeLinkContext(answer, before);
}

async function observeLinkContext(apiKey: string, path: string) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const requests: { endpoint: string; params: Record<string, string>; status: number; at: string }[] = [];
  const signal = AbortSignal.timeout(60_000);
  async function get(endpoint: string, params: Record<string, string>) {
    const url = new URL(`https://api.semble.so/xrpc/${endpoint}`);
    url.search = new URLSearchParams(params).toString();
    const response = await fetch(url, { headers: { "X-API-Key": apiKey }, signal });
    requests.push({ endpoint, params, status: response.status, at: new Date().toISOString() });
    if (!response.ok) throw new Error(`${endpoint}: HTTP ${response.status}`);
    return z.json().parse(await response.json());
  }
  async function all<T>(endpoint: string, schema: z.ZodType<{ pagination: { currentPage: number; totalCount: number; hasMore: boolean } } & Record<string, unknown>>, key: string, pick: (item: unknown) => T) {
    const items: T[] = [];
    for (let p = 1; ; p++) {
      if (p > 20) throw new Error(`${endpoint}: pagination exceeded checker limit`);
      const parsed = schema.parse(await get(endpoint, { url: linkContextUrl, page: String(p), limit: "100" }));
      if (parsed.pagination.currentPage !== p) throw new Error(`${endpoint}: unexpected page`);
      const list = parsed[key];
      if (!Array.isArray(list)) throw new Error(`${endpoint}: missing ${key}`);
      items.push(...list.map(pick));
      if (!parsed.pagination.hasMore) {
        if (items.length !== parsed.pagination.totalCount) throw new Error(`${endpoint}: incomplete enumeration`);
        return items;
      }
      if (!list.length) throw new Error(`${endpoint}: empty page with hasMore`);
    }
  }
  try {
    const savers = (await all("network.cosmik.card.getLibrariesForUrl", librariesPage, "libraries", (item) => librariesPage.shape.libraries.element.parse(item).user.handle)).sort();
    const collections = (await all("network.cosmik.collection.getForUrl", collectionsPage, "collections", (item) => {
      const collection = collectionsPage.shape.collections.element.parse(item);
      return { name: collection.name, owner: collection.author?.handle ?? null };
    })).sort((a, b) => a.name.localeCompare(b.name));
    const notes = (await all("network.cosmik.card.getNoteCardsForUrl", notesPage, "notes", (item) => {
      const note = notesPage.shape.notes.element.parse(item);
      return { author: note.author.handle, note: note.note };
    })).sort((a, b) => a.author.localeCompare(b.author) || a.note.localeCompare(b.note));
    return { status: "ok", evidence: { savers, collections, notes } satisfies LinkContextEvidence } as const;
  } catch (error) {
    return { status: "error", error: error instanceof Error ? error.message : String(error) } as const;
  } finally {
    await writeFile(path, JSON.stringify({ startedAt, elapsedMs: Math.round(performance.now() - start), requests }, null, 2));
  }
}

export async function runLinkContextTask(run: EvalRun) {
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const apiKey = variable ? process.env[variable] : undefined;
  if (!apiKey) throw new Error("Link-context checker requires the server's Semble API key");
  await mkdir(run.outputDir);
  const before = await observeLinkContext(apiKey, join(run.outputDir, "checker-before.json"));
  const status = await runEval(run);
  const after = await observeLinkContext(apiKey, join(run.outputDir, "checker-after.json"));
  const result = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(run.outputDir, "result.json"), "utf8")));
  const grade = linkContextRunGrade(status, result.output, before.status === "ok" ? before.evidence : undefined, after.status === "ok" ? after.evidence : undefined);
  await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({
    gradingVersion: 1, task: { name: "link-context", kind: "link-context" }, executionStatus: status, ...grade,
    expected: before.status === "ok" ? before.evidence : before, after: after.status === "ok" ? "same" : after,
  }, null, 2));
  return grade.verdict;
}
