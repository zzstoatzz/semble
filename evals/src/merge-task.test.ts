import { test } from "node:test";
import assert from "node:assert/strict";
import { gradeCollectionMerge, selectMergeCards, type MergeCard, type MergeCollection } from "./merge-task.js";

const cards: MergeCard[] = ["a", "b", "c"].map((id) => ({ id, url: `https://example.com/${id}`,
  cardContent: { title: id }, note: { id: `note-${id}`, text: `Keep ${id}` }, collections: [] }));
function shelf(id: string, selected: MergeCard[]): MergeCollection {
  return { id, name: id, description: "Keep this", urlCards: selected.map(({ id, url }) => ({ id, url })) };
}
function example() {
  const before = [shelf("left", cards.slice(0, 2)), shelf("right", cards.slice(1))];
  return { executionStatus: "completed", before, after: structuredClone(before), sources: ["left", "right"],
    destination: shelf("merged", cards), extraCollections: [], libraryBefore: cards,
    libraryAfter: cards.map((card) => ({ ...card, collections: [{ id: "merged" }] })) };
}
test("merge fixture has overlap and an exclusive card on both sides", () => {
  const [left, right] = selectMergeCards(cards);
  assert.deepEqual(left.map((card) => card.id), ["a", "b"]);
  assert.deepEqual(right.map((card) => card.id), ["b", "c"]);
  assert.throws(() => selectMergeCards(cards.slice(0, 2)));
});
test("exact union passes without a judge or parsing the answer", () => {
  assert.equal(gradeCollectionMerge(example()).verdict, "pass");
});
test("missing, extra, duplicated and recreated cards fail", () => {
  const [first, , third] = cards;
  if (!first || !third) throw new Error("Missing example cards");
  for (const selected of [cards.slice(0, 2), [...cards, first], [...cards.slice(0, 2), { ...third, id: "recreated" }]]) {
    assert.equal(gradeCollectionMerge({ ...example(), destination: shelf("merged", selected) }).verdict, "fail");
  }
});
test("source deletion, metadata changes and membership changes fail", () => {
  const input = example();
  assert.equal(gradeCollectionMerge({ ...input, after: [] }).verdict, "fail");
  for (const change of [{ name: "renamed" }, { description: "changed" }, { urlCards: [] }]) {
    assert.equal(gradeCollectionMerge({ ...input, after: input.after.map((shelf) => ({ ...shelf, ...change })) }).verdict, "fail");
  }
});
test("notes, card content and unrelated memberships must be preserved", () => {
  for (const change of [{ note: null }, { cardContent: { title: "changed" } }, { collections: [{ id: "other" }] }]) {
    assert.equal(gradeCollectionMerge({ ...example(), libraryAfter: cards.map((card) => ({ ...card, ...change })) }).verdict, "fail");
  }
});
test("execution failure cannot pass with an otherwise correct final state", () => {
  assert.equal(gradeCollectionMerge({ ...example(), executionStatus: "timeout" }).verdict, "fail");
  assert.equal(gradeCollectionMerge({ ...example(), destination: undefined }).verdict, "fail");
  assert.equal(gradeCollectionMerge({ ...example(), extraCollections: ["unexpected"] }).verdict, "fail");
});
