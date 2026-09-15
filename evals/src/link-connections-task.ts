import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { runEval, type EvalRun } from "./runner.js";
import { answerUrlMentions, canonicalUrl } from "./shared-saves-task.js";

export const connectionsUrl = "https://knightcolumbia.org/content/ai-as-normal-technology";

export const linkConnectionsPrompt = `I'm about to read "AI as Normal Technology" (${connectionsUrl}). What have people on Semble connected it to, and how does each connected link relate to it: does it support it, push back on it, build on it, or just relate? Give me every connected link with the relationship as recorded. Don't change anything.`;

const connectionType = z.enum(["SUPPORTS", "OPPOSES", "ADDRESSES", "HELPFUL", "LEADS_TO", "RELATED", "SUPPLEMENT", "EXPLAINER", "REFERENCES", "SAME_AS"]);
const page = z.object({
  connections: z.array(z.object({ connection: z.object({ id: z.string(), type: connectionType, note: z.string().nullish() }), source: z.object({ url: z.string() }), target: z.object({ url: z.string() }) })),
  pagination: z.object({ currentPage: z.number().int(), totalCount: z.number().int().nonnegative(), hasMore: z.boolean() }),
});

export interface LinkConnectionsEvidence {
  edges: { other: string; type: z.infer<typeof connectionType>; direction: "incoming" | "outgoing"; note: string | null }[];
}

/** Words an answer may use for each recorded type. Stems keep "led to" and "opposing" valid. */
const typeWords: Record<z.infer<typeof connectionType>, string[]> = {
  SUPPORTS: ["support"], OPPOSES: ["oppos", "push back", "pushes back", "counter"], ADDRESSES: ["address"], HELPFUL: ["helpful"],
  LEADS_TO: ["leads to", "led to", "lead to", "builds on", "build on", "response to", "responds to"], RELATED: ["related", "relates"],
  SUPPLEMENT: ["supplement"], EXPLAINER: ["explain"], REFERENCES: ["reference"], SAME_AS: ["same as", "same page", "duplicate"],
};

/** A type word counts unless it is negated just before ("nothing opposes", "no support", "doesn't push back"). */
const negation = /(?:\bno|\bnot|\bnothing|\bnone|\bnobody|n't|\bneither|\bnor|\brather than)\W{1,3}(?:\w+\W{1,3}){0,2}$/;

function typesMentioned(passage: string) {
  const text = passage.toLowerCase();
  return (Object.keys(typeWords) as z.infer<typeof connectionType>[]).filter((type) => [type.toLowerCase(), type.toLowerCase().replace(/_/g, " "), ...typeWords[type]].some((word) => {
    let index = text.indexOf(word);
    while (index !== -1) {
      if (!negation.test(text.slice(Math.max(0, index - 40), index))) return true;
      index = text.indexOf(word, index + 1);
    }
    return false;
  }));
}

/** A link's relationship is read from its own list item or paragraph, at most this many characters either side of the url. */
const passageLimit = 400;

const itemMarker = /^[ \t]*(?:[-*•]|\d+[.)])[ \t]/;

/** Offset where the list item or paragraph containing `at` begins. */
function itemStart(text: string, at: number) {
  const blank = text.lastIndexOf("\n\n", at);
  let lineStart = text.lastIndexOf("\n", at - 1) + 1;
  while (lineStart > 0) {
    if (itemMarker.test(text.slice(lineStart, Math.min(text.length, lineStart + 12)))) break;
    lineStart = text.lastIndexOf("\n", lineStart - 2) + 1;
  }
  return Math.max(lineStart, blank === -1 ? 0 : blank);
}

/**
 * Deterministic grade: every connected link appears, and the passage after each one
 * names its recorded relationship and no other relationship type.
 */
export function gradeLinkConnections(answer: string, evidence: LinkConnectionsEvidence) {
  const mentions = answerUrlMentions(answer);
  const expected = evidence.edges.map((edge) => ({ ...edge, url: canonicalUrl(edge.other) }));
  const missing = expected.filter((edge) => !mentions.some((mention) => mention.url === edge.url)).map((edge) => edge.url);
  if (missing.length) return { verdict: "fail", reason: `Answer omits ${missing.length} of ${expected.length} connected links`, missing };
  const anchors = mentions.filter((mention) => expected.some((edge) => edge.url === mention.url)).sort((a, b) => a.at - b.at);
  const mislabeled: { url: string; recorded: string; found: string[] }[] = [];
  for (const edge of expected) {
    const first = anchors.find((mention) => mention.url === edge.url);
    if (!first) continue;
    const next = anchors.find((mention) => mention.at > first.at && mention.url !== edge.url);
    // The relationship lives in the link's own paragraph, which may put the label before or after the url.
    const previous = anchors.filter((mention) => mention.at < first.at && mention.url !== edge.url).at(-1);
    const start = Math.max(previous?.at ?? 0, itemStart(answer, first.at), first.at - passageLimit);
    const paragraphEnd = answer.indexOf("\n\n", first.at);
    const end = Math.min(next?.at ?? answer.length, paragraphEnd === -1 ? answer.length : paragraphEnd, first.at + passageLimit);
    const passage = answer.slice(start, end);
    const found = typesMentioned(passage);
    if (!found.includes(edge.type) || found.some((type) => type !== edge.type)) mislabeled.push({ url: edge.url, recorded: edge.type, found });
  }
  if (mislabeled.length) return { verdict: "fail", reason: `Answer mislabels the relationship for ${mislabeled.length} of ${expected.length} links`, mislabeled };
  return { verdict: "pass", reason: `All ${expected.length} connected links listed with their recorded relationship` };
}

export function linkConnectionsRunGrade(status: Awaited<ReturnType<typeof runEval>>, answer: string, before?: LinkConnectionsEvidence, after?: LinkConnectionsEvidence) {
  if (status !== "completed") return { verdict: "fail", reason: `Agent failed to complete: ${status}`, failureKind: "execution" };
  if (!before || !after) return { verdict: "inconclusive", reason: "Checker could not obtain complete evidence" };
  if (JSON.stringify(before) !== JSON.stringify(after)) return { verdict: "inconclusive", reason: "Connections changed during the run" };
  if (!before.edges.length) return { verdict: "inconclusive", reason: "No connections exist for the url; replace the case input" };
  return gradeLinkConnections(answer, before);
}

async function observeConnections(apiKey: string, path: string) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const requests: { endpoint: string; params: Record<string, string>; status: number; at: string }[] = [];
  const signal = AbortSignal.timeout(60_000);
  try {
    const edges: LinkConnectionsEvidence["edges"] = [];
    const ids = new Set<string>();
    for (let p = 1; ; p++) {
      if (p > 20) throw new Error("connection pagination exceeded checker limit");
      const url = new URL("https://api.semble.so/xrpc/network.cosmik.connection.getForUrl");
      const params = { url: connectionsUrl, page: String(p), limit: "100" };
      url.search = new URLSearchParams(params).toString();
      const response = await fetch(url, { headers: { "X-API-Key": apiKey }, signal });
      requests.push({ endpoint: "network.cosmik.connection.getForUrl", params, status: response.status, at: new Date().toISOString() });
      if (!response.ok) throw new Error(`getForUrl: HTTP ${response.status}`);
      const parsed = page.parse(await response.json());
      if (parsed.pagination.currentPage !== p) throw new Error("unexpected connection page");
      for (const item of parsed.connections) {
        if (ids.has(item.connection.id)) throw new Error("repeated connection during pagination");
        ids.add(item.connection.id);
        const incoming = canonicalUrl(item.target.url) === canonicalUrl(connectionsUrl);
        edges.push({ other: incoming ? item.source.url : item.target.url, type: item.connection.type, direction: incoming ? "incoming" : "outgoing", note: item.connection.note ?? null });
      }
      if (!parsed.pagination.hasMore) {
        if (ids.size !== parsed.pagination.totalCount) throw new Error("incomplete connection enumeration");
        break;
      }
      if (!parsed.connections.length) throw new Error("empty connection page with hasMore");
    }
    edges.sort((a, b) => a.other.localeCompare(b.other) || a.type.localeCompare(b.type));
    return { status: "ok", evidence: { edges } satisfies LinkConnectionsEvidence } as const;
  } catch (error) {
    return { status: "error", error: error instanceof Error ? error.message : String(error) } as const;
  } finally {
    await writeFile(path, JSON.stringify({ startedAt, elapsedMs: Math.round(performance.now() - start), requests }, null, 2));
  }
}

export async function runLinkConnectionsTask(run: EvalRun) {
  const variable = run.server.headersFromEnv["X-API-Key"] ?? run.server.headersFromEnv["x-semble-api-key"];
  const apiKey = variable ? process.env[variable] : undefined;
  if (!apiKey) throw new Error("Link-connections checker requires the server's Semble API key");
  await mkdir(run.outputDir);
  const before = await observeConnections(apiKey, join(run.outputDir, "checker-before.json"));
  const status = await runEval(run);
  const after = await observeConnections(apiKey, join(run.outputDir, "checker-after.json"));
  const result = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(run.outputDir, "result.json"), "utf8")));
  const grade = linkConnectionsRunGrade(status, result.output, before.status === "ok" ? before.evidence : undefined, after.status === "ok" ? after.evidence : undefined);
  await writeFile(join(run.outputDir, "evaluation.json"), JSON.stringify({
    gradingVersion: 1, task: { name: "link-connections", kind: "link-connections" }, executionStatus: status, ...grade,
    expected: before.status === "ok" ? before.evidence : before, after: after.status === "ok" ? "same" : after,
  }, null, 2));
  return grade.verdict;
}
