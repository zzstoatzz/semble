import assert from "node:assert/strict";
import { test } from "node:test";
import { runMatrixJobs } from "./matrix.js";

test("matrix bounds concurrent jobs and continues after failures", async () => {
  let active = 0;
  let peak = 0;
  let started = 0;
  const releases: (() => void)[] = [];
  const jobs = Array.from({ length: 5 }, (_, index) => async () => {
    started++;
    active++;
    peak = Math.max(peak, active);
    if (index < 2) await new Promise<void>((resolve) => releases.push(resolve));
    active--;
    if (index === 1) throw new Error("fixture failure");
    return index;
  });
  const pending = runMatrixJobs(jobs, 2);
  assert.equal(started, 2);
  for (const release of releases) release();
  const results = await pending;
  assert.equal(peak, 2);
  assert.equal(started, 5);
  assert.equal(results[1]?.status, "rejected");
  assert.deepEqual(results[4], { status: "fulfilled", value: 4 });
});
