import { mkdir, readFile, writeFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { parseArgs } from "node:util";
import { ModelRuntime } from "@earendil-works/pi-coding-agent";
import { readMatrix, serverHeaders } from "./config.js";
import { connectMcp } from "./mcp.js";
import { runEval } from "./runner.js";
import { z } from "zod";
import { RecommendationCase, recommendationPrompt, runRecommendationTask } from "./recommendation-task.js";
import { runSharedSavesTask, sharedSavesPrompt } from "./shared-saves-task.js";
import { summarizeEvaluations } from "./summary.js";
import { compareTaskAnswers } from "./comparison.js";
import { runCollectionMerge, mergeTaskPrompt } from "./merge-task.js";
import { runMatrixJobs } from "./matrix.js";

async function main() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      config: { type: "string", default: "matrix.json" },
      prompt: { type: "string" }, model: { type: "string", multiple: true }, server: { type: "string", multiple: true },
      task: { type: "string", multiple: true },
      repetitions: { type: "string" }, "dry-run": { type: "boolean" },
      output: { type: "string", default: "results" }, help: { type: "boolean" },
    },
  });
  const command = positionals[0] ?? "run";
  const selectedTasks = [...positionals.slice(1), ...(values.task ?? [])];
  if (values.help) {
    console.log(`Pi eval harness

  just evals                                     # default suite
  just evals tasks                               # list cases
  just evals run reading-recommendation library-filing     # select cases
  just evals run reading-recommendation --model luna --model haiku
  just evals run --server code-mode --repetitions 3
  just evals run --dry-run                        # show selection without calls
  just evals models
  just evals inspect [--server official]
  just evals run --prompt path/to/prompt.txt

Options: --config matrix.json --output results
Omitted task selection runs the suite. Models default to defaultModels in the
matrix; --model all selects the catalog. Repeat --model or --server for subsets.
Each cell gets a fresh Pi session using existing provider authentication.`);
    return;
  }
  if (!["models", "tasks", "inspect", "run"].includes(command) || (command !== "run" && selectedTasks.length)) {
    throw new Error("Expected models, tasks, inspect, or run [task ...]; use --help");
  }
  if (command === "models") {
    const runtime = await ModelRuntime.create();
    for (const model of await runtime.getAvailable()) console.log(`${model.provider}/${model.id}`);
    return;
  }
  const matrix = await readMatrix(resolve(values.config));
  if (values.repetitions) matrix.repetitions = z.coerce.number().int().positive().parse(values.repetitions);
  const modelNames = values.model ?? matrix.defaultModels ?? matrix.models.map((model) => model.name);
  const serverNames = values.server ?? matrix.servers.map((server) => server.name);
  for (const requested of modelNames) {
    if (requested !== "all" && !matrix.models.some((model) => model.name === requested)) throw new Error(`Unknown model: ${requested}`);
  }
  for (const requested of serverNames) {
    if (!matrix.servers.some((server) => server.name === requested)) throw new Error(`Unknown server: ${requested}`);
  }
  const models = matrix.models.filter((model) => modelNames.includes("all") || modelNames.includes(model.name));
  const servers = matrix.servers.filter((server) => serverNames.includes(server.name));
  if (command === "inspect") {
    for (const server of servers) serverHeaders(server);
    for (const server of servers) {
      const connection = await connectMcp(server, AbortSignal.timeout(matrix.timeoutSeconds * 1000));
      try {
        console.log(JSON.stringify({ server: server.name, tools: connection.inventory }, null, 2));
      } finally {
        await connection.client.close();
      }
    }
    return;
  }
  // Graded entirely from API state: no answer judge, no pairwise comparison.
  const judgeFreeTasks = new Set(["collection-merge", "shared-saves"]);
  const libraryCases = z.array(RecommendationCase).parse(JSON.parse(await readFile(new URL("../tasks/library.json", import.meta.url), "utf8")));
  for (const requested of selectedTasks) {
    if (requested !== "suite" && !judgeFreeTasks.has(requested) && !libraryCases.some((task) => task.name === requested)) throw new Error(`Unknown task: ${requested}`);
  }
  if (selectedTasks.length && values.prompt) throw new Error("Choose tasks or --prompt");
  const registered = [...libraryCases.map((task) => ({ name: task.name, prompt: recommendationPrompt(task),
    run: (run: Parameters<typeof runEval>[0]) => runRecommendationTask(run, task) })),
    { name: "shared-saves", prompt: sharedSavesPrompt, run: runSharedSavesTask },
    { name: "collection-merge", prompt: mergeTaskPrompt, run: runCollectionMerge }];
  if (command === "tasks") {
    for (const task of registered) console.log(`${task.name}: ${task.prompt}`);
    return;
  }
  const tasks = values.prompt
    ? [{ name: "prompt", prompt: await readFile(resolve(values.prompt), "utf8"), run: runEval }]
    : registered.filter((task) => !selectedTasks.length || selectedTasks.includes("suite") || selectedTasks.includes(task.name));
  if (tasks.some((task) => !task.prompt.trim())) throw new Error("Prompt file is empty");
  if (values["dry-run"]) {
    console.log(JSON.stringify({ tasks: tasks.map((task) => task.name), models: models.map((model) => model.name),
      servers: servers.map((server) => server.name), repetitions: matrix.repetitions, concurrency: matrix.concurrency,
      runs: tasks.length * models.length * servers.length * matrix.repetitions, judge: tasks.every((task) => judgeFreeTasks.has(task.name) || task.name === "prompt") ? null : matrix.judge }, null, 2));
    return;
  }
  for (const server of servers) serverHeaders(server);
  const runtime = await ModelRuntime.create();
  const available = await runtime.getAvailable();
  for (const model of tasks.every((task) => judgeFreeTasks.has(task.name) || task.name === "prompt") ? models : [...models, matrix.judge]) {
    if (!available.some((candidate) => candidate.provider === model.provider && candidate.id === model.id)) {
      throw new Error(`${model.name}: ${model.provider}/${model.id} is unavailable. Run the models command and configure an exact authenticated model ID.`);
    }
  }
  const outputDir = resolve(values.output, new Date().toISOString().replaceAll(":", "-") + `-${process.pid}`);
  await mkdir(outputDir, { recursive: true });
  await writeFile(join(outputDir, "matrix.json"), JSON.stringify({ ...matrix, models, servers, defaultModels: models.map((model) => model.name) }, null, 2));
  await writeFile(join(outputDir, "tasks.json"), JSON.stringify(tasks.map(({ name, prompt }) => ({ name, prompt })), null, 2));
  const onlyTask = tasks.length === 1 ? tasks[0] : undefined;
  if (onlyTask) await writeFile(join(outputDir, "prompt.txt"), onlyTask.prompt);
  console.log(`Results: ${outputDir}`);
  let failures = 0;
  const jobs: (() => Promise<string>)[] = [];
  for (const task of tasks) {
    for (let repetition = 1; repetition <= matrix.repetitions; repetition++) {
      for (const model of models) {
        for (const server of servers) {
          const name = `${tasks.length > 1 ? task.name + "--" : ""}${model.name}--${server.name}--${repetition}`;
          const run = { matrix, model, server, prompt: task.prompt, runtime, outputDir: join(outputDir, name) };
          jobs.push(async () => {
            console.log(`${name}: started`);
            const status = await task.run(run);
            console.log(`${name}: ${status}`);
            if (status !== "completed" && status !== "pass") failures++;
            return status;
          });
        }
      }
    }
  }
  const results = await runMatrixJobs(jobs, matrix.concurrency);
  for (const result of results) {
    if (result.status === "rejected") {
      failures++;
      console.error(result.reason instanceof Error ? result.reason.message : String(result.reason));
    }
  }
  if (!values.prompt && servers.length === 2) {
    const comparisons: (() => Promise<void>)[] = [];
    for (const task of tasks.filter((task) => !judgeFreeTasks.has(task.name))) for (const model of models) for (let repetition = 1; repetition <= matrix.repetitions; repetition++) {
      comparisons.push(() => compareTaskAnswers({ root: outputDir, matrix: { ...matrix, servers }, model, task,
        repetition, multipleTasks: tasks.length > 1, runtime }));
    }
    if (comparisons.length) console.log("Comparing passing answers blind, in both orders");
    await runMatrixJobs(comparisons, matrix.concurrency);
  }
  if (!values.prompt) await summarizeEvaluations(outputDir);
  if (failures) process.exitCode = 1;
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
