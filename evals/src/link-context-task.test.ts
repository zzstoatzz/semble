import assert from "node:assert/strict";
import { test } from "node:test";
import { gradeLinkContext, linkContextRunGrade, type LinkContextEvidence } from "./link-context-task.js";

const evidence: LinkContextEvidence = {
  savers: ["bmann.ca", "atproto.science", "byarielm.fyi"],
  collections: [{ name: "Data Ownership", owner: "bmann.ca" }, { name: "protocols", owner: null }],
  notes: [{ author: "bmann.ca", note: "organizational data layer" }, { author: "byarielm.fyi", note: "unclear category" }],
};
const good = "Saved by @bmann.ca, atproto.science and byarielm.fyi. Filed under “Data Ownership” and protocols. Notes: bmann.ca calls it an organizational data layer; byarielm.fyi says the category is unclear.";

test("complete link context passes, case-insensitively", () => {
  assert.equal(gradeLinkContext(good, evidence).verdict, "pass");
  assert.equal(gradeLinkContext(good.toUpperCase(), evidence).verdict, "pass");
});

test("a missing saver, collection, or note author fails with the count", () => {
  assert.match(gradeLinkContext(good.replace("atproto.science", "someone"), evidence).reason, /1 of 3 savers/);
  assert.match(gradeLinkContext(good.replace("protocols", "misc"), evidence).reason, /1 of 2 collections/);
  const noNotes = "Saved by bmann.ca, atproto.science and byarielm.fyi. Filed under Data Ownership and protocols.";
  assert.equal(gradeLinkContext(noNotes, evidence).verdict, "pass");
  const missingAuthor = { ...evidence, notes: [...evidence.notes, { author: "third.person", note: "x" }] };
  assert.match(gradeLinkContext(good, missingAuthor).reason, /1 note authors/);
});

test("drift and execution failure are not graded as answers", () => {
  assert.equal(linkContextRunGrade("turn_limit", good, evidence, evidence).verdict, "fail");
  assert.equal(linkContextRunGrade("completed", good, evidence, { ...evidence, savers: ["bmann.ca"] }).verdict, "inconclusive");
  assert.equal(linkContextRunGrade("completed", good, evidence, evidence).verdict, "pass");
});
