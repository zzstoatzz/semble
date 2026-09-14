import assert from "node:assert/strict";
import { test } from "node:test";
import { gradeSharedSaves, sharedFromLibraries, sharedSavesRunGrade, type SharedSavesEvidence } from "./shared-saves-task.js";

const libraries: SharedSavesEvidence["libraries"] = [
  { handle: "hyl.st", urls: ["https://a.example/one", "https://b.example/two/", "https://solo.example/h"] },
  { handle: "zafarali.me", urls: ["https://a.example/one", "https://b.example/two", "https://c.example/three"] },
  { handle: "finest.day", urls: ["https://a.example/one", "https://solo.example/f"] },
  { handle: "aaronstevenwhite.io", urls: ["https://c.example/three"] },
  { handle: "tgoerke.bsky.social", urls: [] },
  { handle: "blue-phia.bsky.social", urls: ["https://a.example/one-more"] },
];
const evidence: SharedSavesEvidence = { libraries, shared: sharedFromLibraries(libraries) };

const correct = `Three links are saved by more than one of them:
- https://a.example/one — saved by hyl.st, zafarali.me and finest.day
- https://b.example/two/ — hyl.st and zafarali.me
- https://c.example/three — zafarali.me, aaronstevenwhite.io`;

test("shared links are computed with trailing-slash equivalence", () => {
  assert.deepEqual(evidence.shared, [
    { url: "https://a.example/one", savers: ["finest.day", "hyl.st", "zafarali.me"] },
    { url: "https://b.example/two", savers: ["hyl.st", "zafarali.me"] },
    { url: "https://c.example/three", savers: ["aaronstevenwhite.io", "zafarali.me"] },
  ]);
});

test("a complete, correctly attributed answer passes", () => {
  assert.equal(gradeSharedSaves(correct, evidence).verdict, "pass");
});

test("a longer URL sharing a prefix does not count as the shorter one", () => {
  const answer = correct.replace("https://a.example/one —", "https://a.example/one-more —");
  assert.equal(gradeSharedSaves(answer, evidence).verdict, "fail");
});

test("omitting a shared link fails", () => {
  const grade = gradeSharedSaves(correct.replace(/- https:\/\/c.example.*$/m, ""), evidence);
  assert.equal(grade.verdict, "fail");
  assert.match(grade.reason, /omits 1 of 3/);
});

test("listing a link only one person saved fails", () => {
  const grade = gradeSharedSaves(`${correct}\n- https://solo.example/h — hyl.st`, evidence);
  assert.equal(grade.verdict, "fail");
  assert.match(grade.reason, /only one person/);
});

test("naming the wrong savers fails", () => {
  const grade = gradeSharedSaves(correct.replace("hyl.st and zafarali.me", "hyl.st and finest.day"), evidence);
  assert.equal(grade.verdict, "fail");
  assert.match(grade.reason, /misattributes/);
});

test("execution failures and drifting evidence are not graded as answers", () => {
  assert.equal(sharedSavesRunGrade("timeout", correct, evidence, evidence).verdict, "fail");
  assert.equal(sharedSavesRunGrade("completed", correct, evidence, undefined).verdict, "inconclusive");
  const drifted = { ...evidence, libraries: libraries.map((library) => library.handle === "finest.day" ? { ...library, urls: ["https://solo.example/f"] } : library) };
  assert.equal(sharedSavesRunGrade("completed", correct, evidence, drifted).verdict, "inconclusive");
  assert.equal(sharedSavesRunGrade("completed", correct, evidence, evidence).verdict, "pass");
});
