export async function runMatrixJobs<T>(jobs: readonly (() => Promise<T>)[], concurrency: number) {
  if (!Number.isInteger(concurrency) || concurrency < 1) throw new Error("Concurrency must be a positive integer");
  const results: PromiseSettledResult<T>[] = [];
  let next = 0;
  async function worker() {
    while (next < jobs.length) {
      const index = next++;
      const job = jobs[index];
      if (!job) throw new Error("Missing matrix job");
      try {
        results[index] = { status: "fulfilled", value: await job() };
      } catch (reason) {
        results[index] = { status: "rejected", reason };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(concurrency, jobs.length) }, worker));
  return results;
}
