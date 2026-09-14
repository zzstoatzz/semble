import assert from "node:assert/strict";
import { mkdir, mkdtemp } from "node:fs/promises";
import { join } from "node:path";
import { test } from "node:test";
import { ModelRuntime } from "@earendil-works/pi-coding-agent";
import { gradeJudgeChecks, judgeAnswer } from "./judge.js";
import { readMatrix } from "./config.js";

// These exercise judging, not Semble task performance. No frozen API is supplied to actors.
test("a correct required answer cannot override failed consistency", () => {
  assert.equal(gradeJudgeChecks({
    requiredAnswer: { passed: true, reason: "Correct winner and count" },
    consistency: { passed: false, reason: "Invented second winner" },
  }).passed, false);
});

test("live judge regression controls", { skip: process.env.SEMBLE_LIVE_JUDGE_TEST !== "1" }, async (t) => {
  const matrix = await readMatrix("matrix.json");
  const runtime = await ModelRuntime.create();
  await mkdir("results", { recursive: true });
  const directory = await mkdtemp(join("results", "judge-regression-"));
  t.diagnostic(`Evidence: ${directory}`);
  const task = "Which shared URL has the most library saves? Give any tied winner and its count.";
  const rubric = "The shared URLs and library counts are https://lexicon.garden/ = 22, " +
    "https://atproto.at/ = 17, https://panproto.dev/ = 14, https://quickslice.slices.network/ = 5. " +
    "There is exactly one winner. Prose and code fences are allowed. Extra claims must be consistent with these facts.";
  const controls = [
    { name: "recorded-haiku-false-tie", answer: "Now I'll compare the URLs in both collections to find shared ones and identify which has the highest library count.\n\n**Collection 1 (ca9cbf0b-fc76-43e5-a676-05a7262b08a9): \"atproto things\"** - 79 cards\n**Collection 2 (21d2b63c-2131-412a-b9b8-13aa6f6637d7): \"atproto tools \u2692\ufe0f\"** - 51 cards\n\nLet me identify URLs that appear in both collections:\n\nFrom Collection 1, URLs that also appear in Collection 2:\n1. **https://panproto.dev/** - Collection 1: `urlLibraryCount: 14`, Collection 2: `urlLibraryCount: 14`\n2. **https://lexicon.garden/** - Collection 1: `urlLibraryCount: 22`, Collection 2: `urlLibraryCount: 22`\n3. **https://quickslice.slices.network/** - Collection 1: `urlLibraryCount: 5`, Collection 2: `urlLibraryCount: 5`\n4. **https://atproto.at/** - Collection 1: `urlLibraryCount: 17`, Collection 2: `urlLibraryCount: 17`\n\n## Result\n\nThe collections share **4 URLs** in common. Among these shared URLs, there are two tied for the highest library save count:\n\n**Winner(s):**\n- **URL:** `https://lexicon.garden/`\n- **Library Count:** **22**\n\n(Alternatively, the same URL also appears with 22 libraries, so if you need just one answer: `https://lexicon.garden/` with **22 libraries** is among the highest, tied with one other result. However, `https://lexicon.garden/` is the highest shared URL.)\n\n**Shared URLs Summary:**\n1. `https://lexicon.garden/` - **22 libraries** \u2713 HIGHEST\n2. `https://atproto.at/` - 17 libraries\n3. `https://panproto.dev/` - 14 libraries\n4. `https://quickslice.slices.network/` - 5 libraries", rubric, passed: false },
    { name: "correct-prose", answer: "Lexicon Garden (https://lexicon.garden/) wins with 22 library saves.", rubric, passed: true },
    { name: "wrong-metric", answer: "https://panproto.dev/ wins with 20 collections, which means 20 library saves.", rubric, passed: false },
    { name: "false-tie", answer: "https://lexicon.garden/ has 22 saves and is tied with another URL for first place.", rubric, passed: false },
    { name: "valid-tie", answer: "https://lexicon.garden/ has 22 saves, tied for first.", rubric: "Exactly two shared URLs tie for first: https://lexicon.garden/ and https://atproto.at/, each with 22 library saves. Any one is acceptable.", passed: true },
    { name: "empty-overlap", answer: "There are no shared URLs.", rubric: "The intersection is empty; an explicit statement of no shared URLs is correct.", passed: true },
  ];
  for (const control of controls) {
    await t.test(control.name, async () => {
      const outputDir = join(directory, control.name);
      await mkdir(outputDir);
      const verdict = await judgeAnswer({ task, ...control, model: matrix.judge, runtime, outputDir });
      assert.equal(verdict.passed, control.passed, verdict.reason);
    });
  }
});
