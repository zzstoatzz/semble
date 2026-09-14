import assert from "node:assert/strict";
import { test } from "node:test";
import { collectionRunGrade, compareCollectionEvidence, type CollectionEvidence } from "./collection-task.js";

const evidence: CollectionEvidence = {
  collections: [{ id: "a", urls: ["a", "b", "c"] }, { id: "b", urls: ["a", "b", "c"] }],
  counts: [{ url: "a", saveCount: 10 }, { url: "b", saveCount: 10 }, { url: "c", saveCount: 5 }],
};

test("checker establishes the complete tied winner set independently of the answer", () => {
  const result = compareCollectionEvidence(evidence, evidence);
  assert.equal(result.verdict, "stable");
  assert.deepEqual(result.winners, ["a", "b"]);
  assert.equal(result.maximum, 10);
});

test("grader distinguishes live drift from wrong answers", () => {
  const changed = structuredClone(evidence);
  changed.counts.push({ url: "new", saveCount: 20 });
  assert.equal(compareCollectionEvidence(evidence, changed).verdict, "inconclusive");
});

test("empty overlap differs from a shared URL with zero saves", () => {
  const empty: CollectionEvidence = { collections: [], counts: [] };
  assert.equal(compareCollectionEvidence(empty, empty).maximum, null);
  const zero: CollectionEvidence = { collections: [], counts: [{ url: "a", saveCount: 0 }] };
  assert.equal(compareCollectionEvidence(zero, zero).maximum, 0);
  assert.deepEqual(compareCollectionEvidence(zero, zero).winners, ["a"]);
});


test("execution failures remain failures even when checker evidence is missing or changed", () => {
  for (const status of ["timeout", "output_limit", "turn_limit", "error"] as const) {
    assert.equal(collectionRunGrade(status).verdict, "fail");
    assert.equal(collectionRunGrade(status, evidence, { ...evidence, counts: [] }).verdict, "fail");
  }
  assert.equal(collectionRunGrade("completed").verdict, "inconclusive");
});
