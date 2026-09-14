import { readdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { z } from "zod";

async function optionalJson(path: string) {
  try { return z.json().parse(JSON.parse(await readFile(path, "utf8"))); }
  catch (error) {
    if (error instanceof Error && "code" in error && error.code === "ENOENT") return undefined;
    throw error;
  }
}
const usage = z.object({ usage: z.object({ cost: z.number() }).nullish() });
const judgeReport = usage.extend({ verdict: z.object({ quality: z.object({ personalization: z.number(), decisionValue: z.number(), evidence: z.number() }).optional() }).optional() });
const actor = usage.extend({ server: z.string(), model: z.object({ name: z.string() }), elapsedMs: z.number(), toolErrors: z.number() });
const evaluation = z.object({ verdict: z.string(), reason: z.string(), task: z.object({ name: z.string() }), model: z.string().optional(), server: z.string().optional() });

export async function summarizeEvaluations(root: string) {
  const rows = [];
  let actorCost = 0, judgeCost = 0, pairwiseCost = 0;
  for (const entry of await readdir(root, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name === "comparisons") continue;
    const path = join(root, entry.name);
    const gradeFile = await optionalJson(join(path, "evaluation.json"));
    if (!gradeFile) continue;
    const grade = evaluation.parse(gradeFile);
    const resultFile = await optionalJson(join(path, "result.json"));
    const result = resultFile ? actor.parse(resultFile) : undefined;
    const judgeFile = await optionalJson(join(path, "judge.json"));
    const judging = judgeFile ? judgeReport.parse(judgeFile) : undefined;
    actorCost += result?.usage?.cost ?? 0;
    judgeCost += judging?.usage?.cost ?? 0;
    rows.push({ run: entry.name, task: grade.task.name, model: result?.model.name ?? grade.model,
      server: result?.server ?? grade.server, verdict: grade.verdict, reason: grade.reason, quality: judging?.verdict?.quality ?? null,
      seconds: result ? result.elapsedMs / 1000 : null, toolErrors: result?.toolErrors ?? null,
      actorCost: result?.usage?.cost ?? null, judgeCost: judging?.usage?.cost ?? null });
  }
  const comparisons = [];
  const comparisonRoot = join(root, "comparisons");
  const entries = await readdir(comparisonRoot).catch((error: NodeJS.ErrnoException) => {
    if (error.code === "ENOENT") return [];
    throw error;
  });
  for (const entry of entries) {
    const result = await optionalJson(join(comparisonRoot, entry, "comparison.json"));
    if (result) comparisons.push({ pair: entry, result });
    for (const order of ["forward", "swapped"]) {
      const file = await optionalJson(join(comparisonRoot, entry, order, "judge.json"));
      if (file) pairwiseCost += usage.parse(file).usage?.cost ?? 0;
    }
  }
  const costs = { actor: actorCost, judge: judgeCost, pairwise: pairwiseCost, reportedTotal: actorCost + judgeCost + pairwiseCost };
  await writeFile(join(root, "summary.json"), JSON.stringify({ rows, comparisons, costs }, null, 2));
  const table = ["| Task | Model | MCP | Pass | Fail | Inconclusive |", "|---|---|---|---:|---:|---:|"];
  const groups = new Map<string, { pass: number; fail: number; inconclusive: number }>();
  for (const row of rows) {
    const key = `${row.task} | ${row.model ?? "not run"} | ${row.server ?? "not run"}`;
    const counts = groups.get(key) ?? { pass: 0, fail: 0, inconclusive: 0 };
    if (row.verdict === "pass") counts.pass++;
    else if (row.verdict === "fail") counts.fail++;
    else counts.inconclusive++;
    groups.set(key, counts);
  }
  for (const [key, counts] of groups) table.push(`| ${key} | ${counts.pass} | ${counts.fail} | ${counts.inconclusive} |`);
  const report = `${table.join("\n")}\n\nReported cost: $${costs.reportedTotal.toFixed(4)} (actors $${actorCost.toFixed(4)}, judges $${judgeCost.toFixed(4)}, pairwise $${pairwiseCost.toFixed(4)}). Missing individual costs remain null in summary.json.\n`;
  await writeFile(join(root, "summary.md"), report);
  console.log(report);
}
