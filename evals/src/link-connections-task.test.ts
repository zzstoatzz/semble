import assert from "node:assert/strict";
import { test } from "node:test";
import { gradeLinkConnections, linkConnectionsRunGrade, type LinkConnectionsEvidence } from "./link-connections-task.js";

const evidence: LinkConnectionsEvidence = { edges: [
  { other: "https://a.example/critique", type: "OPPOSES", direction: "incoming", note: "pushes back" },
  { other: "https://b.example/followup", type: "LEADS_TO", direction: "incoming", note: null },
  { other: "https://c.example/context/", type: "RELATED", direction: "incoming", note: null },
] };
const good = `Three links are connected:
- https://a.example/critique — opposes it; the curator says it pushes back on the framing.
- https://b.example/followup — recorded as leads to: a response written after the piece.
- https://c.example/context — just related, no note.`;

test("a faithful answer passes, with slash and stem tolerance", () => {
  assert.equal(gradeLinkConnections(good, evidence).verdict, "pass");
  assert.equal(gradeLinkConnections(good.replace("recorded as leads to", "which led to"), evidence).verdict, "pass");
});

test("a negated type word or a distant summary does not count as a relabel", () => {
  const summary = `${good}\n\nNothing here opposes it directly; the critique is the only pushback and the rest either build on or relate to it.`;
  assert.equal(gradeLinkConnections(summary, evidence).verdict, "pass");
  const far = `${good}\n\n${"filler ".repeat(80)}This piece supports a broader thesis.`;
  assert.equal(gradeLinkConnections(far, evidence).verdict, "pass");
});

test("omitting a connected link fails", () => {
  assert.match(gradeLinkConnections(good.replace(/- https:\/\/c.example.*$/m, ""), evidence).reason, /omits 1 of 3/);
});

test("relabeling a relationship fails, including adding a second type", () => {
  assert.match(gradeLinkConnections(good.replace("just related, no note", "supports the argument"), evidence).reason, /mislabels/);
  assert.match(gradeLinkConnections(good.replace("opposes it;", "opposes it, and in a way supports it;"), evidence).reason, /mislabels/);
});

test("drift, empty evidence, and execution failure are not graded as answers", () => {
  assert.equal(linkConnectionsRunGrade("timeout", good, evidence, evidence).verdict, "fail");
  assert.equal(linkConnectionsRunGrade("completed", good, evidence, { edges: evidence.edges.slice(1) }).verdict, "inconclusive");
  assert.equal(linkConnectionsRunGrade("completed", good, { edges: [] }, { edges: [] }).verdict, "inconclusive");
  assert.equal(linkConnectionsRunGrade("completed", good, evidence, evidence).verdict, "pass");
});
