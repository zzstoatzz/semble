import assert from "node:assert/strict";
import { test } from "node:test";
import { collectionAuditRunGrade, gradeCollectionAudit, type CollectionAuditEvidence } from "./collection-audit-task.js";

const evidence: CollectionAuditEvidence = {
  sparseCollections: [{ name: "Drafts", cardCount: 0 }, { name: "Maps & GIS", cardCount: 1 }],
  uncollectedUrls: ["https://a.example/one", "https://b.example/two/"],
};
const good = "Empty: Drafts. Single card: Maps & GIS. Not in any collection: https://a.example/one and https://b.example/two";

test("complete audit passes with trailing-slash tolerance", () => {
  assert.equal(gradeCollectionAudit(good, evidence).verdict, "pass");
});

test("omissions fail with counts", () => {
  assert.match(gradeCollectionAudit(good.replace("Drafts", "Draft folder"), evidence).reason, /1 of 2 sparse collections/);
  assert.match(gradeCollectionAudit(good.replace(" and https://b.example/two", ""), evidence).reason, /1 of 2 uncollected links/);
});

test("drift and execution failure are not graded as answers", () => {
  assert.equal(collectionAuditRunGrade("timeout", good, evidence, evidence).verdict, "fail");
  assert.equal(collectionAuditRunGrade("completed", good, evidence, { ...evidence, uncollectedUrls: [] }).verdict, "inconclusive");
  assert.equal(collectionAuditRunGrade("completed", good, evidence, evidence).verdict, "pass");
});
