import assert from "node:assert/strict";
import test from "node:test";
import { answerReadingUrls, normalizeReadingUrl, sameReadingLibrary, recommendationPrompt, type ReadingLibrary } from "./recommendation-task.js";

test("reading novelty ignores fragments and tracking but preserves meaningful query parameters", () => {
  assert.equal(normalizeReadingUrl("https://example.org/read?utm_source=mail#section"), "https://example.org/read");
  assert.notEqual(normalizeReadingUrl("https://example.org/read?id=1"), normalizeReadingUrl("https://example.org/read?id=2"));
});
test("natural prose and Markdown links are extracted without an answer format requirement", () => {
  assert.deepEqual(answerReadingUrls("Try [this](https://example.org/read). Based on https://example.org/saved."), ["https://example.org/read", "https://example.org/saved"]);
  assert.deepEqual(answerReadingUrls("**[Read](https://example.org/article)**"), ["https://example.org/article"]);
  assert.deepEqual(answerReadingUrls("I can't recommend anything."), []);
  assert.deepEqual(answerReadingUrls("[Read](https://example.org/Article_(topic))"), ["https://example.org/Article_(topic)"]);
});
test("library drift includes changed interest evidence, not just URL membership", () => {
  const before: ReadingLibrary = [{ id: "1", url: "https://example.org/", cardContent: { url: "https://example.org/", title: "Gardening" }, collections: [], note: { text: "Try this" } }];
  assert.equal(sameReadingLibrary(before, structuredClone(before)), true);
  const after = structuredClone(before);
  if (after[0]) after[0].note = { text: "No longer interested" };
  assert.equal(sameReadingLibrary(before, after), false);
  assert.equal(sameReadingLibrary(before, []), false);
});
test("recommendation prompt specifies user intent without any inferred interests", () => {
  const prompt = recommendationPrompt({ name: "test", identifier: "someone.example", kind: "reading" });
  assert.match(prompt, /someone.example/);
  assert.doesNotMatch(prompt, /ATProto|gardening|painting|local-first|Boris/);
});
