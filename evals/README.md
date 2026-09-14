# semble pi evals

a TypeScript harness that runs [Pi](https://github.com/earendil-works/pi) against the official Semble MCP and this repo's code-mode MCP. Pi owns the agent loop; the harness selects the model and server, supplies a prompt, and records the run. two tasks exercise personalized reading decisions and complete library organization against independent live API evidence.

## use

requires Node.js 22.19+ and configured Pi provider authentication.

```sh
just evals-install
just evals models
just evals inspect
just evals run --prompt /path/to/prompt.txt --model haiku
just evals run reading-recommendation library-filing
just evals run --model luna --model haiku
just evals run --dry-run
```

run these commands from the repository root. `just evals` loads the root `.env` when present; existing environment variables take precedence. set `SEMBLE_API_KEY` there or export it before inspecting or running. arguments pass through unchanged, with relative paths resolved from `evals/`. `just evals --help` shows the available commands.

edit [matrix.json](matrix.json) to choose models, server URLs, repetitions, and limits. use positional task names and repeat `--model` or `--server` to select subsets. `just evals` runs the default suite; `just evals tasks` lists available cases. `--model all` selects every configured model, and `--repetitions` changes the sample count. `--config experiment.local.json` selects another matrix. provider/model IDs must exactly match the `models` command; the runner never substitutes another model.

`concurrency` bounds complete runs, including their fact checks and judge calls. jobs have independent sessions and result directories; one failure does not cancel the rest. provider rate-limit failures remain recorded failures rather than silently retried successes.

the matrix uses Pi's `openai-codex` route for Luna/Terra and direct Anthropic for Haiku/Sonnet. Pi resolves existing credentials and custom models normally. MCP header values come from environment variables; the matrix stores only their names.

## results

the [suite](../docs/portable-eval-suite.md) establishes the facts using direct API observations before and after each run. a separately configured Pi judge grades the natural-language answer against those facts and returns a structured verdict. it writes its verdict, checker evidence, and judge usage separately from the actor's execution result. the judge assesses the required answer and consistency of additional claims separately; both must pass. observed data changes, incomplete checker data, or judge failures are inconclusive for completed actors. actor execution failures remain failures even when checker evidence is unavailable. arbitrary `--prompt` runs have execution metrics but no correctness verdict.

each invocation writes an ignored directory under `results/`, with the selected matrix and prompt. each model/server/repetition gets its own directory containing the MCP tool inventory, effective request configuration, complete message and tool events, and a result with output, elapsed time, turns, tool errors, tokens, and Pi's estimated cost. streaming deltas are omitted because completed messages retain the content.

`completed` means the model finished normally, not that it answered correctly. timeouts, exhausted output or turn limits, and provider/setup failures are recorded separately. a failed run does not prevent remaining matrix cells from running; the command exits nonzero if any cell fails. cost is Pi's model-price estimate, not a billing receipt; subscription routes may report zero. tool metrics distinguish discovery, execution, and ordinary operations, with durations and UTF-8 text sizes. per-response token usage and stop reasons are saved separately. text sizes exclude images and are not token counts; overlapping tool durations must not be summed as wall time. nested API calls are unobserved, represented as null rather than zero. existing run evidence cannot be overwritten.

each run starts with empty history and only the selected server's tools. ambient skills, extensions, context files, prompt templates, compaction, and Pi automatic retries are disabled. Pi adds the same working-directory line to the configured system prompt; the effective prompt is captured. tool names, descriptions, and input schemas are preserved. MCP text and images become Pi content, other content blocks become JSON text, and MCP tool errors enter Pi's normal error-recovery loop.

the configured servers are live and expose writes as well as reads. prompts determine the requested actions. traces contain prompts and tool results and stay local under the ignored results directory. this harness does not seed or reset Semble data.

## develop

```sh
just evals-check        # TypeScript + real Pi/MCP loop against local fixtures; no inference spend
just evals-judge-check  # configured judge against fixed grading controls; uses inference
```

## metrics and tiers

`summary.md` reports per task/model/server: pass, fail, inconclusive, infra, pass@1, pass^3, median seconds, and tool errors, plus a table of tool errors by failing method. infra counts runs that never reached the model (a checker preflight failure or a provider error before any response) and is excluded from the pass rates; pass^3 is tau-bench's pass^k, the probability that three independent runs all pass. the summary refuses to combine cells whose checkers have different `gradingVersion` values.

`just evals-smoke <tasks...>` runs one repetition per cell for tuning the server or a task. numbers to report come from `just evals run` at the configured repetitions, on tasks that were not tuned against.
