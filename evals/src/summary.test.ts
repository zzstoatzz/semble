import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { failedToolName } from "./runner.js";
import { isInfrastructureFailure, passHatK, summarizeEvaluations } from "./summary.js";

test("pass^k follows tau-bench's definition", () => {
  assert.equal(passHatK(10, 10, 3), 1);
  assert.equal(passHatK(10, 0, 3), 0);
  assert.equal(passHatK(2, 2, 3), null);
  assert.ok(Math.abs((passHatK(10, 7, 3) ?? 0) - 35 / 120) < 1e-9);
});

test("infrastructure failures are preflight or pre-model provider errors", () => {
  assert.equal(isInfrastructureFailure({ executionStatus: "not_run" }), true);
  assert.equal(isInfrastructureFailure({ executionStatus: "error" }, { status: "error", modelResponses: [] }), true);
  assert.equal(isInfrastructureFailure({ executionStatus: "error" }, { status: "error", modelResponses: [{}] }), false);
  assert.equal(isInfrastructureFailure({ executionStatus: "timeout" }, { status: "timeout", modelResponses: [{}] }), false);
});

test("failedToolName names the innermost nested method for execute", () => {
  const nested = "Error calling tool 'execute': Exception: Error calling tool 'search_get_accounts': Error: jwt signature does not match jwt issuer";
  assert.equal(failedToolName("execute", "execution", nested), "search_get_accounts");
  assert.equal(failedToolName("execute", "execution", "SyntaxError: bad code"), "execute");
  assert.equal(failedToolName("list_user_cards", "operation", "boom"), "list_user_cards");
});

test("summary reports medians, tool errors and failures by method", async () => {
  const root = await mkdtemp(join(tmpdir(), "semble-summary-test-"));
  const cells = [
    { name: "reading--luna--code-mode--1", verdict: "fail", elapsedMs: 41000, toolErrors: 2, calls: [{ status: "error", failedTool: "search_get_accounts" }, { status: "error", failedTool: "search_get_accounts" }, { status: "success", failedTool: null }] },
    { name: "reading--luna--code-mode--2", verdict: "pass", elapsedMs: 61000, toolErrors: 0, calls: [{ status: "success", failedTool: null }] },
    { name: "reading--luna--official--1", verdict: "pass", elapsedMs: 30000, toolErrors: 0, calls: [] },
    { name: "reading--luna--official--2", verdict: "fail", elapsedMs: 1000, toolErrors: 0, calls: [], status: "error", responses: [] , executionStatus: "error" },
  ];
  for (const cell of cells) {
    const directory = join(root, cell.name);
    await mkdir(directory);
    await writeFile(join(directory, "evaluation.json"), JSON.stringify({ verdict: cell.verdict, reason: "fixture", task: { name: "reading" }, gradingVersion: 2, executionStatus: cell.executionStatus ?? "completed" }));
    await writeFile(join(directory, "result.json"), JSON.stringify({ server: cell.name.includes("official") ? "official" : "code-mode", model: { name: "luna" }, status: cell.status ?? "completed", elapsedMs: cell.elapsedMs, toolErrors: cell.toolErrors, mcpCalls: cell.calls, modelResponses: cell.responses ?? [{}], usage: { cost: 0.01 } }));
  }
  await summarizeEvaluations(root);
  const report = await readFile(join(root, "summary.md"), "utf8");
  assert.match(report, /\| reading \| luna \| code-mode \| 1 \| 1 \| 0 \| 0 \| 0\.50 \| - \| 51 \| 2 \|/);
  assert.match(report, /\| reading \| luna \| official \| 1 \| 0 \| 0 \| 1 \| 1\.00 \| - \| 30 \| 0 \|/);
  assert.match(report, /\| reading \| luna \| code-mode \| search_get_accounts \| 2 \|/);
  assert.match(report, /Reported cost: \$0\.0400/);
});

test("summary refuses to merge cells graded by different checker versions", async () => {
  const root = await mkdtemp(join(tmpdir(), "semble-summary-mixed-"));
  for (const [name, version] of [["t--luna--official--1", 1], ["t--luna--official--2", 2]] as const) {
    await mkdir(join(root, name));
    await writeFile(join(root, name, "evaluation.json"), JSON.stringify({ verdict: "pass", reason: "fixture", task: { name: "t" }, gradingVersion: version, executionStatus: "completed" }));
    await writeFile(join(root, name, "result.json"), JSON.stringify({ server: "official", model: { name: "luna" }, status: "completed", elapsedMs: 1000, toolErrors: 0, mcpCalls: [], modelResponses: [{}] }));
  }
  await assert.rejects(summarizeEvaluations(root), /different checker versions/);
});
