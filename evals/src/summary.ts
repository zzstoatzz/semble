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
const mcpCall = z.object({ status: z.string(), failedTool: z.string().nullable().optional() });
const actor = usage.extend({ server: z.string(), model: z.object({ name: z.string() }), status: z.string().optional(), elapsedMs: z.number(), toolErrors: z.number(), mcpCalls: z.array(mcpCall).optional(), modelResponses: z.array(z.unknown()).optional() });

function median(values: number[]) {
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  if (!sorted.length) return null;
  return sorted.length % 2 ? sorted[middle] ?? null : ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}
const evaluation = z.object({ verdict: z.string(), reason: z.string(), task: z.object({ name: z.string() }), model: z.string().optional(), server: z.string().optional(), gradingVersion: z.number().optional(), executionStatus: z.string().optional() });

function choose(n: number, k: number) {
  if (k < 0 || k > n) return 0;
  let result = 1;
  for (let i = 1; i <= k; i++) result = (result * (n - k + i)) / i;
  return result;
}

/** pass^k from tau-bench: probability that k independent draws all pass, given successes among trials. */
export function passHatK(trials: number, successes: number, k: number) {
  if (trials < k) return null;
  return choose(successes, k) / choose(trials, k);
}

/**
 * A run that never reached the model is infrastructure, not a model result: the checker
 * failed preflight, or the actor errored before any model response arrived.
 */
export function isInfrastructureFailure(grade: { executionStatus?: string }, result?: { status?: string; modelResponses?: unknown[] }) {
  if (grade.executionStatus === "not_run") return true;
  return result?.status === "error" && (result.modelResponses?.length ?? 0) === 0;
}

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
    rows.push({ run: entry.name, task: grade.task.name, gradingVersion: grade.gradingVersion ?? null, model: result?.model.name ?? grade.model,
      server: result?.server ?? grade.server, verdict: grade.verdict, reason: grade.reason, quality: judging?.verdict?.quality ?? null,
      infrastructure: isInfrastructureFailure(grade, result),
      seconds: result ? result.elapsedMs / 1000 : null, toolErrors: result?.toolErrors ?? null,
      failedTools: result?.mcpCalls?.flatMap((call) => call.status === "error" && call.failedTool ? [call.failedTool] : []) ?? [],
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
  const table = ["| Task | Model | MCP | Pass | Fail | Inconclusive | Infra | pass@1 | pass^3 | Median s | Tool errors |", "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"];
  const groups = new Map<string, { pass: number; fail: number; inconclusive: number; infrastructure: number; seconds: number[]; toolErrors: number; failures: Map<string, number>; gradingVersions: Set<number | null> }>();
  for (const row of rows) {
    const key = `${row.task} | ${row.model ?? "not run"} | ${row.server ?? "not run"}`;
    const counts = groups.get(key) ?? { pass: 0, fail: 0, inconclusive: 0, infrastructure: 0, seconds: [], toolErrors: 0, failures: new Map<string, number>(), gradingVersions: new Set<number | null>() };
    counts.gradingVersions.add(row.gradingVersion);
    if (row.infrastructure) counts.infrastructure++;
    else if (row.verdict === "pass") counts.pass++;
    else if (row.verdict === "fail") counts.fail++;
    else counts.inconclusive++;
    if (row.seconds !== null && !row.infrastructure) counts.seconds.push(row.seconds);
    counts.toolErrors += row.toolErrors ?? 0;
    for (const tool of row.failedTools) counts.failures.set(tool, (counts.failures.get(tool) ?? 0) + 1);
    groups.set(key, counts);
  }
  const mixed = [...groups].filter(([, counts]) => counts.gradingVersions.size > 1).map(([key]) => key);
  if (mixed.length) throw new Error(`Refusing to summarize cells graded by different checker versions: ${mixed.join("; ")}`);
  for (const [key, counts] of groups) {
    const trials = counts.pass + counts.fail + counts.inconclusive;
    const seconds = median(counts.seconds);
    const passAt1 = trials ? (counts.pass / trials).toFixed(2) : "-";
    const passHat3 = passHatK(trials, counts.pass, 3);
    table.push(`| ${key} | ${counts.pass} | ${counts.fail} | ${counts.inconclusive} | ${counts.infrastructure} | ${passAt1} | ${passHat3 === null ? "-" : passHat3.toFixed(2)} | ${seconds === null ? "-" : seconds.toFixed(0)} | ${counts.toolErrors} |`);
  }
  const failures = ["| Task | Model | MCP | Failing method | Errors |", "|---|---|---|---|---:|"];
  for (const [key, counts] of groups) {
    for (const [tool, count] of [...counts.failures].sort((a, b) => b[1] - a[1])) failures.push(`| ${key} | ${tool} | ${count} |`);
  }
  const failureSection = failures.length > 2 ? `\n\nTool errors by method (the innermost method named in each error):\n\n${failures.join("\n")}` : "";
  const legend = "\n\nInfra counts runs that never reached the model (preflight failure or provider error before any response); they are excluded from pass@1 and pass^3. pass^3 is the chance that three independent runs all pass. Inconclusive counts against pass@1.";
  const report = `${table.join("\n")}${legend}${failureSection}\n\nReported cost: $${costs.reportedTotal.toFixed(4)} (actors $${actorCost.toFixed(4)}, judges $${judgeCost.toFixed(4)}, pairwise $${pairwiseCost.toFixed(4)}). Missing individual costs remain null in summary.json.\n`;
  await writeFile(join(root, "summary.md"), report);
  console.log(report);
}
