import assert from "node:assert/strict";
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { failedToolName } from "./runner.js";
import { summarizeEvaluations } from "./summary.js";

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
  ];
  for (const cell of cells) {
    const directory = join(root, cell.name);
    await mkdir(directory);
    await writeFile(join(directory, "evaluation.json"), JSON.stringify({ verdict: cell.verdict, reason: "fixture", task: { name: "reading" } }));
    await writeFile(join(directory, "result.json"), JSON.stringify({ server: cell.name.includes("official") ? "official" : "code-mode", model: { name: "luna" }, elapsedMs: cell.elapsedMs, toolErrors: cell.toolErrors, mcpCalls: cell.calls, usage: { cost: 0.01 } }));
  }
  await summarizeEvaluations(root);
  const report = await readFile(join(root, "summary.md"), "utf8");
  assert.match(report, /\| reading \| luna \| code-mode \| 1 \| 1 \| 0 \| 51 \| 2 \|/);
  assert.match(report, /\| reading \| luna \| official \| 1 \| 0 \| 0 \| 30 \| 0 \|/);
  assert.match(report, /\| reading \| luna \| code-mode \| search_get_accounts \| 2 \|/);
  assert.match(report, /Reported cost: \$0\.0300/);
});
