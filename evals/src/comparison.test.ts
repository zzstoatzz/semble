import assert from "node:assert/strict";
import test from "node:test";
import { resolvePreference } from "./comparison.js";
import { advisoryQuality, qualityGrade } from "./recommendation-task.js";

test("preference is mapped back from reversed order and disagreement is retained", () => {
  assert.equal(resolvePreference("A", "B"), "A");
  assert.equal(resolvePreference("B", "A"), "B");
  assert.equal(resolvePreference("A", "A"), "order-sensitive");
  assert.equal(resolvePreference("tie", "tie"), "tie");
  assert.equal(resolvePreference(undefined, "B"), "inconclusive");
});
test("factual correctness cannot hide shallow quality or missing evidence", () => {
  const base = { passed: true, evidenceSufficient: true, reason: "Correct", requiredAnswer: { passed: true, reason: "Correct" }, consistency: { passed: true, reason: "Correct" } };
  assert.equal(qualityGrade({ ...base, quality: { personalization: 3, decisionValue: 2, evidence: 4 } }).verdict, "fail");
  assert.equal(qualityGrade({ ...base, quality: { personalization: 3, decisionValue: 3, evidence: 3 } }).verdict, "pass");
  assert.equal(qualityGrade(base).verdict, "inconclusive");
  assert.deepEqual(advisoryQuality({ ...base, quality: { personalization: 3, decisionValue: 2, evidence: 4 } }).quality, { personalization: 3, decisionValue: 2, evidence: 4 });
  assert.equal(advisoryQuality(base).quality, null);
});
