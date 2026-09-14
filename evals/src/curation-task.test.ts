import assert from "node:assert/strict";
import test from "node:test";
import { checkCurationPage, compareCurationEvidence, curationPrompt, type CurationEvidence } from "./curation-task.js";

test("curation evidence ignores ordering but detects edits, removals, and new records", () => {
  const a = { id: "a", note: "Interesting", author: { id: "did:a", handle: "a.example" } };
  const b = { id: "b", note: "Unclear", author: { id: "did:b", handle: "b.example" } };
  const before: CurationEvidence = { notes: [a, b], connections: [] };
  assert.equal(compareCurationEvidence(before, { notes: [b, a], connections: [] }), true);
  assert.equal(compareCurationEvidence(before, { notes: [a], connections: [] }), false);
  assert.equal(compareCurationEvidence(before, { notes: [a, { ...b, note: "Changed" }], connections: [] }), false);
  assert.equal(compareCurationEvidence({ notes: [], connections: [] }, { notes: [], connections: [] }), true);
});

test("checker rejects partial, repeated, drifting, and empty intermediate pages", () => {
  assert.throws(() => checkCurationPage({ ids: new Set() }, 1, { currentPage: 1, totalCount: 2, hasMore: false }, ["a"]), /Incomplete/);
  const state = { ids: new Set<string>() };
  checkCurationPage(state, 1, { currentPage: 1, totalCount: 2, hasMore: true }, ["a"]);
  assert.throws(() => checkCurationPage(state, 2, { currentPage: 2, totalCount: 2, hasMore: false }, ["a"]), /Repeated/);
  assert.throws(() => checkCurationPage(state, 2, { currentPage: 2, totalCount: 3, hasMore: false }, ["b"]), /changed/);
  assert.throws(() => checkCurationPage({ ids: new Set() }, 1, { currentPage: 1, totalCount: 2, hasMore: true }, []), /Empty/);
  checkCurationPage(state, 2, { currentPage: 2, totalCount: 2, hasMore: false }, ["b"]);
  checkCurationPage({ ids: new Set() }, 1, { currentPage: 1, totalCount: 0, hasMore: false }, []);
});

test("prompts depend on user context, not observed notes or relationships", () => {
  const prompt = curationPrompt({ name: "arbitrary-case", kind: "context", url: "https://example.org/" });
  assert.match(prompt, /https:\/\/example.org\//);
  assert.doesNotMatch(prompt, /OPPOSES|RELATED|template|disagreement|Boris|Joel/);
});

test("live curation judge accepts empty evidence and faithful summaries but rejects invented claims", { skip: process.env.SEMBLE_LIVE_CURATION_JUDGE_TEST !== "1" }, async (t) => {
  const { mkdir, mkdtemp } = await import("node:fs/promises");
  const { join } = await import("node:path");
  const { ModelRuntime } = await import("@earendil-works/pi-coding-agent");
  const { readMatrix } = await import("./config.js");
  const { judgeAnswer } = await import("./judge.js");
  const { curationRubric } = await import("./curation-task.js");
  const matrix = await readMatrix("matrix.json");
  const runtime = await ModelRuntime.create();
  await mkdir("results", { recursive: true });
  const directory = await mkdtemp(join("results", "curation-judge-controls-"));
  t.diagnostic(`Evidence: ${directory}`);
  const task = { name: "control", kind: "notes", url: "https://example.org/" } as const;
  const populated: CurationEvidence = { notes: [
    { id: "1", author: { id: "did:a", handle: "alex.example" }, note: "The description says this is a publishing tool. I haven't tried it." },
    { id: "2", author: { id: "did:b", handle: "bea.example" }, note: "I'm unsure what this does." },
  ], connections: [] };
  const contextTask = { name: "context-control", kind: "context", url: "https://example.org/" } as const;
  const contextEvidence: CurationEvidence = { notes: [], connections: [
    { connection: { id: "a", type: "RELATED", note: "A tutorial for beginners", curator: { id: "did:a", handle: "alex.example" } }, source: { url: "https://example.org/" }, target: { url: "https://tutorial.example/" } },
    { connection: { id: "b", type: "OPPOSES", note: "A critique of the approach", curator: { id: "did:a", handle: "alex.example" } }, source: { url: "https://critique.example/" }, target: { url: "https://example.org/" } },
  ] };
  const controls = [
    { name: "empty", evidence: { notes: [], connections: [] }, answer: "I found no notes about this URL in Semble, so I can't draw a conclusion from them.", passed: true },
    { name: "faithful", evidence: populated, answer: "There isn't much evidence to go on. Alex describes it as a publishing tool based on its description and hasn't tried it; Bea is unsure what it does.", passed: true },
    { name: "invented-consensus", evidence: populated, answer: "Everyone agrees it is a great publishing tool. Both Alex and Bea have tested and recommend it.", passed: false },
    { name: "false-empty", evidence: populated, answer: "Nobody has written anything about this URL in Semble.", passed: false },
    { name: "valid-selection", task: contextTask, evidence: contextEvidence, answer: "For getting started, I'd look at https://tutorial.example/: Alex linked it as a beginner tutorial. There is also a critique at https://critique.example/, which Alex connected as opposing the original approach.", passed: true },
    { name: "reverse-relationship", task: contextTask, evidence: contextEvidence, answer: "Alex says the original source opposes https://critique.example/, so the original is a rebuttal to that critique.", passed: false },
    { name: "missing-coverage", evidence: populated, answer: "Alex describes it as a publishing tool without having tried it, and Bea is unsure. It has 80 library saves.", passed: true },
  ];
  for (const control of controls) await t.test(control.name, async () => {
    const outputDir = join(directory, control.name);
    await mkdir(outputDir);
    const verdict = await judgeAnswer({ task: curationPrompt(control.task ?? task), rubric: curationRubric(control.task ?? task, control.evidence),
      answer: control.answer, model: matrix.judge, runtime, outputDir });
    if (control.name === "missing-coverage") {
      assert.equal(verdict.evidenceSufficient, false, verdict.reason);
      return;
    }
    assert.equal(verdict.evidenceSufficient, true, verdict.reason);
    assert.equal(verdict.passed, control.passed, verdict.reason);
  });
});
