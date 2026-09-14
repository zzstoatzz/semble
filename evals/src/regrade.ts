import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";
import { gradeCollectionAudit } from "./collection-audit-task.js";
import { gradeSharedSaves, sharedFromLibraries, type SharedSavesEvidence } from "./shared-saves-task.js";

/** Re-grade stored shared-saves and collection-audit cells with the current grader (coverage and attribution only). */
const root = process.argv[2];
if (!root) throw new Error("usage: regrade <results dir>");
const shared = z.object({ task: z.object({ name: z.string() }), verdict: z.string(), reason: z.string(), expected: z.array(z.object({ url: z.string(), savers: z.array(z.string()) })).nullable().optional() });
const audit = z.object({ task: z.object({ name: z.string() }), verdict: z.string(), reason: z.string(), expected: z.object({ sparseCollections: z.array(z.object({ name: z.string(), cardCount: z.number() })), uncollectedUrls: z.array(z.string()) }).nullable().optional() });
for (const entry of (await readdir(root, { withFileTypes: true })).filter((e) => e.isDirectory() && e.name !== "comparisons")) {
  const dir = join(root, entry.name);
  const raw = JSON.parse(await readFile(join(dir, "evaluation.json"), "utf8"));
  const output = z.object({ output: z.string() }).parse(JSON.parse(await readFile(join(dir, "result.json"), "utf8"))).output;
  if (raw.task?.name === "shared-saves" || raw.task?.kind === "shared-saves") {
    const e = shared.parse(raw);
    if (!e.expected) continue;
    const evidence: SharedSavesEvidence = { libraries: e.expected.flatMap((x) => x.savers.map((handle) => ({ handle, urls: [x.url] }))), shared: e.expected };
    if (JSON.stringify(sharedFromLibraries(evidence.libraries)) !== JSON.stringify(e.expected)) throw new Error("evidence reconstruction mismatch");
    const g = gradeSharedSaves(output, evidence);
    console.log(`${entry.name}: stored=${e.verdict} regraded=${g.verdict} | ${g.reason}`);
  } else if (raw.task?.name === "collection-audit") {
    const e = audit.parse(raw);
    if (!e.expected) continue;
    const g = gradeCollectionAudit(output, e.expected);
    console.log(`${entry.name}: stored=${e.verdict} regraded=${g.verdict} | ${g.reason}`);
  }
}
