import { appendFileSync } from "node:fs";
import { mkdir, mkdtemp, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { CallToolResultSchema } from "@modelcontextprotocol/sdk/types.js";
import {
  createAgentSession, DefaultResourceLoader, ModelRuntime,
  SessionManager, SettingsManager, type AgentSessionEvent,
} from "@earendil-works/pi-coding-agent";
import type { EvalMatrix, ModelCase, ServerCase } from "./config.js";
import { connectMcp, mcpTool } from "./mcp.js";

export interface EvalRun {
  matrix: EvalMatrix;
  model: ModelCase;
  server: ServerCase;
  prompt: string;
  outputDir: string;
  runtime: ModelRuntime;
}

interface McpCallMetric {
  id: string;
  name: string;
  category: "discovery" | "execution" | "operation";
  startedAt: string;
  elapsedMs: number | null;
  status: "pending" | "success" | "error";
  textBytes: number | null;
  contentBlocks: number | null;
  /** The innermost tool named in an error: the nested SDK method for execute, the tool itself otherwise. */
  failedTool: string | null;
}

export function failedToolName(toolName: string, category: McpCallMetric["category"], text: string) {
  if (category !== "execution") return toolName;
  const names = [...text.matchAll(/Error calling tool '([^']+)'/g)].map((match) => match[1]);
  return names.at(-1) ?? toolName;
}

export async function runEval(run: EvalRun) {
  const startedAt = new Date().toISOString();
  const start = performance.now();
  const model = run.runtime.getModel(run.model.provider, run.model.id);
  if (!model) throw new Error(`Unknown model: ${run.model.provider}/${run.model.id}`);
  // A run directory is immutable evidence: never append a new run to old events.
  await mkdir(run.outputDir, { recursive: true });
  if ((await readdir(run.outputDir)).some((name) => ["result.json", "events.jsonl", "request.json"].includes(name))) {
    throw new Error("Run directory already contains evidence");
  }
  await writeFile(join(run.outputDir, "run.lock"), startedAt, { flag: "wx" });
  const cwd = process.cwd();
  const agentDir = await mkdtemp(join(tmpdir(), "semble-eval-"));
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(new Error("Run timed out")), run.matrix.timeoutSeconds * 1000);
  let session: Awaited<ReturnType<typeof createAgentSession>>["session"] | undefined;
  let connection: Awaited<ReturnType<typeof connectMcp>> | undefined;
  let turns = 0;
  let toolErrors = 0;
  const limit = { reached: false };
  let status: "completed" | "error" | "timeout" | "turn_limit" | "output_limit" = "error";
  let stopReason: string | undefined;
  const calls = new Map<string, { start: number; metric: McpCallMetric }>();
  const responses: { stopReason: string; usage: Extract<Extract<AgentSessionEvent, { type: "message_end" }>["message"], { role: "assistant" }>["usage"] }[] = [];
  let errorMessage: string | undefined;
  try {
    connection = await connectMcp(run.server, controller.signal);
    await writeFile(join(run.outputDir, "tools.json"), JSON.stringify(connection.inventory, null, 2));
    const settingsManager = SettingsManager.inMemory({
      compaction: { enabled: false }, retry: { enabled: false },
    });
    const resourceLoader = new DefaultResourceLoader({
      cwd, agentDir, settingsManager,
      noExtensions: true, noSkills: true, noPromptTemplates: true,
      noThemes: true, noContextFiles: true,
      systemPrompt: run.matrix.systemPrompt,
      appendSystemPromptOverride: () => [],
    });
    await resourceLoader.reload();
    const client = connection.client;
    const customTools = connection.inventory.map((tool) => mcpTool(client, tool));
    ({ session } = await createAgentSession({
      cwd, agentDir, model: { ...model, maxTokens: Math.min(model.maxTokens, run.matrix.maxOutputTokens) }, modelRuntime: run.runtime,
      thinkingLevel: run.model.thinking,
      tools: customTools.map((tool) => tool.name), customTools,
      resourceLoader, settingsManager, sessionManager: SessionManager.inMemory(cwd),
    }));
    await writeFile(join(run.outputDir, "request.json"), JSON.stringify({
      startedAt, piVersion: "0.85.1", model: run.model,
      resolvedModel: { provider: model.provider, id: model.id, api: model.api, cost: model.cost },
      thinking: session.thinkingLevel, server: run.server,
      prompt: run.prompt, systemPrompt: session.agent.state.systemPrompt,
      timeoutSeconds: run.matrix.timeoutSeconds, maxTurns: run.matrix.maxTurns,
      maxOutputTokens: Math.min(model.maxTokens, run.matrix.maxOutputTokens),
      tools: session.agent.state.tools.map((tool) => tool.name),
    }, null, 2));
    const activeSession = session;
    const abort = () => { void activeSession.abort(); };
    controller.signal.addEventListener("abort", abort, { once: true });
    session.subscribe((event) => {
      // Final message events contain complete content; omitting streaming deltas
      // avoids duplicating growing partial messages in the trace.
      if (event.type !== "message_update") {
        appendFileSync(join(run.outputDir, "events.jsonl"), JSON.stringify({ at: new Date().toISOString(), event }) + "\n");
      }
      if (event.type === "tool_execution_end" && event.isError) toolErrors++;
      if (event.type === "tool_execution_start") {
        const has = (name: string) => connection?.inventory.some((tool) => tool.name === name) ?? false;
        const codeMode = has("execute") && has("get_schema");
        // a search transform (fastmcp's regex/bm25/jev) exposes the same two-step
        // shape as code mode: find a tool, then run it through a proxy
        const searchMode = has("search_tools") && has("call_tool");
        const discovery = codeMode ? ["search", "get_schema"] : searchMode ? ["search_tools"] : [];
        const execution = codeMode ? "execute" : searchMode ? "call_tool" : null;
        calls.set(event.toolCallId, { start: performance.now(), metric: {
          id: event.toolCallId, name: event.toolName,
          category: discovery.includes(event.toolName) ? "discovery"
            : event.toolName === execution ? "execution" : "operation",
          startedAt: new Date().toISOString(), elapsedMs: null, status: "pending", textBytes: null, contentBlocks: null, failedTool: null,
        } });
      }
      if (event.type === "tool_execution_end") {
        const call = calls.get(event.toolCallId);
        if (call) {
          const result = CallToolResultSchema.parse(event.result);
          call.metric.elapsedMs = Math.round(performance.now() - call.start);
          call.metric.status = event.isError ? "error" : "success";
          call.metric.contentBlocks = result.content.length;
          call.metric.textBytes = result.content.reduce((total, block) =>
            total + (block.type === "text" ? Buffer.byteLength(block.text, "utf8") : 0), 0);
          if (event.isError) {
            const text = result.content.map((block) => block.type === "text" ? block.text : "").join("\n");
            call.metric.failedTool = failedToolName(call.metric.name, call.metric.category, text);
          }
        }
      }
      if (event.type === "message_end" && event.message.role === "assistant") {
        responses.push({ stopReason: event.message.stopReason, usage: event.message.usage });
      }
      if (event.type === "turn_end" && ++turns >= run.matrix.maxTurns && event.message.role === "assistant" && event.message.stopReason === "toolUse") {
        limit.reached = true;
        controller.abort(new Error("Turn limit reached"));
      }
    });
    try {
      controller.signal.throwIfAborted();
      await session.prompt(run.prompt, { expandPromptTemplates: false });
      if (!controller.signal.aborted) {
        const last = session.messages.at(-1);
        if (last?.role === "assistant") stopReason = last.stopReason;
        if (stopReason === "length") status = "output_limit";
        if (last?.role !== "assistant" || last.stopReason !== "stop") {
          throw new Error(last?.role === "assistant" ? last.errorMessage ?? `Model stopped: ${last.stopReason}` : "No final assistant response");
        }
        status = "completed";
      }
    } finally {
      controller.signal.removeEventListener("abort", abort);
    }
  } catch (error) {
    errorMessage = error instanceof Error ? error.message : String(error);
  } finally {
    clearTimeout(timeout);
    if (controller.signal.aborted) {
      status = limit.reached ? "turn_limit" : "timeout";
      errorMessage ??= String(controller.signal.reason);
    }
    const last = session?.messages.findLast((message) => message.role === "assistant");
    const result = {
      status, error: errorMessage, startedAt, elapsedMs: Math.round(performance.now() - start),
      model: run.model, server: run.server.name, turns, toolErrors,
      stopReason: stopReason ?? last?.stopReason,
      metricsVersion: 2,
      mcpCalls: [...calls.values()].map((call) => call.metric),
      nestedApiCalls: null, // Remote execute internals are not exposed by these MCPs.
      modelResponses: responses,
      output: last?.role === "assistant" ? last.content.filter((block) => block.type === "text").map((block) => block.text).join("\n") : "",
      usage: session?.getSessionStats(),
    };
    try {
      await writeFile(join(run.outputDir, "result.json"), JSON.stringify(result, null, 2));
    } finally {
      session?.dispose();
      await connection?.client.close();
      await rm(agentDir, { recursive: true, force: true });
    }
  }
  return status;
}
