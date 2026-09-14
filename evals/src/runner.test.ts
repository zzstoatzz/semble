import assert from "node:assert/strict";
import { once } from "node:events";
import { createServer } from "node:http";
import { mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { ModelRuntime } from "@earendil-works/pi-coding-agent";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";
import { EvalMatrix } from "./config.js";
import { runEval } from "./runner.js";
import { judgeAnswer } from "./judge.js";

// Real Pi and MCP SDKs; only the external inference/service responses are fixtures.
for (const mode of ["success", "empty-output", "tool-error", "turn-limit", "timeout", "provider-error", "output-limit", "judge", "judge-contradiction"] as const) {
  test(`Pi loop: ${mode}`, async () => {
    const directory = await mkdtemp(join(tmpdir(), "semble-eval-test-"));
    const mcp = new McpServer({ name: "fixture", version: "1" });
    let calls = 0;
    const toolName = mode === "empty-output" ? "execute" : "lookup";
    if (mode === "empty-output") mcp.registerTool("get_schema", { inputSchema: {} }, async () => ({ content: [] }));
    mcp.registerTool(toolName, { description: "Look up a value", inputSchema: { key: z.string() } }, async ({ key }) => {
      calls++;
      assert.equal(key, "test");
      if (mode === "empty-output") return { content: [] };
      return { content: [{ type: "text", text: mode === "tool-error" ? "fixture failure" : "fixture value" }], isError: mode === "tool-error" };
    });
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: () => "fixture-session" });
    await mcp.connect(transport);
    const requests: string[] = [];
    const http = createServer(async (request, response) => {
      if (request.url === "/mcp") {
        await transport.handleRequest(request, response);
        return;
      }
      let body = "";
      for await (const chunk of request) body += chunk;
      requests.push(body);
      if (mode === "timeout") return;
      if (mode === "provider-error") {
        response.writeHead(400, { "content-type": "application/json" });
        response.end(JSON.stringify({ error: { message: "fixture provider failure", type: "invalid_request_error" } }));
        return;
      }
      response.writeHead(200, { "content-type": "text/event-stream" });
      const toolTurn = requests.length === 1 || mode === "turn-limit";
      const delta = toolTurn
        ? { role: "assistant", tool_calls: [{ index: 0, id: "call_fixture", type: "function", function: mode.startsWith("judge") ? { name: "submit_verdict", arguments: JSON.stringify({ evidenceSufficient: true, requiredAnswer: { passed: true, reason: "The stated URL and count match." }, consistency: { passed: mode !== "judge-contradiction", reason: mode === "judge-contradiction" ? "A false tie is claimed." : "No contradictory claims." } }) } : { name: toolName, arguments: '{"key":"test"}' } }] }
        : { role: "assistant", content: "Finished fixture lookup." };
      response.write(`data: ${JSON.stringify({ id: "fixture", object: "chat.completion.chunk", created: 1, model: "fixture", choices: [{ index: 0, delta, finish_reason: null }] })}\n\n`);
      response.write(`data: ${JSON.stringify({ id: "fixture", object: "chat.completion.chunk", created: 1, model: "fixture", choices: [{ index: 0, delta: {}, finish_reason: toolTurn ? "tool_calls" : mode === "output-limit" ? "length" : "stop" }], usage: { prompt_tokens: 20, completion_tokens: 10, total_tokens: 30 } })}\n\n`);
      response.end("data: [DONE]\n\n");
    });
    http.listen(0, "127.0.0.1");
    await once(http, "listening");
    const address = http.address();
    assert(address && typeof address !== "string");
    const baseUrl = `http://127.0.0.1:${address.port}`;
    try {
      const runtime = await ModelRuntime.create({ authPath: join(directory, "auth.json"), modelsPath: null, modelsStorePath: join(directory, "catalog.json"), refreshOnCreate: false });
      runtime.registerProvider("fixture", {
        baseUrl: `${baseUrl}/v1`, api: "openai-completions", apiKey: "fixture-key",
        models: [{ id: "fixture", name: "Fixture", reasoning: false, input: ["text"], cost: { input: 1, output: 1, cacheRead: 0, cacheWrite: 0 }, contextWindow: 10000, maxTokens: 100 }],
      });
      const matrix = EvalMatrix.parse({
        models: [{ name: "fixture", provider: "fixture", id: "fixture", thinking: "off" }],
        servers: [{ name: "fixture", url: `${baseUrl}/mcp` }],
        repetitions: 1, timeoutSeconds: mode === "timeout" ? 1 : 15,
        maxTurns: mode === "turn-limit" ? 1 : 5,
        maxOutputTokens: 50,
        systemPrompt: "Use the lookup tool to answer.",
      });
      const [model] = matrix.models;
      const [server] = matrix.servers;
      assert(model && server);
      const outputDir = join(directory, "result");
      if (mode.startsWith("judge")) {
        await mkdir(outputDir);
        const verdict = await judgeAnswer({ task: "Find the winner", rubric: "Winner is a with 10 saves", answer: "a has ten saves.", model, runtime, outputDir });
        assert.equal(verdict.passed, mode !== "judge-contradiction");
        assert.equal(requests.length, 1);
        assert.equal(calls, 0);
        const inference = z.object({ tools: z.array(z.object({ function: z.object({ name: z.string() }) })) }).parse(JSON.parse(requests[0] ?? "null"));
        assert.deepEqual(inference.tools.map((tool) => tool.function.name), ["submit_verdict"]);
        return;
      }
      const status = await runEval({ matrix, model, server, prompt: "Look up test.", outputDir, runtime });
      assert.equal(status, mode === "turn-limit" ? "turn_limit" : mode === "timeout" ? "timeout" : mode === "provider-error" ? "error" : mode === "output-limit" ? "output_limit" : "completed");
      const result = z.object({ turns: z.number(), toolErrors: z.number(), output: z.string(), mcpCalls: z.array(z.object({ elapsedMs: z.number().nullable(), status: z.string(), textBytes: z.number().nullable(), category: z.string(), failedTool: z.string().nullable() })), nestedApiCalls: z.null(), usage: z.object({ tokens: z.object({ total: z.number() }) }) }).parse(JSON.parse(await readFile(join(outputDir, "result.json"), "utf8")));
      if (mode === "success" || mode === "tool-error" || mode === "empty-output") {
        assert.equal(calls, 1);
        assert.equal(result.mcpCalls.length, 1);
        assert.equal(result.mcpCalls[0]?.category, mode === "empty-output" ? "execution" : "operation");
        assert.equal(result.mcpCalls[0]?.status, mode === "tool-error" ? "error" : "success");
        assert.equal(result.mcpCalls[0]?.failedTool, mode === "tool-error" ? "lookup" : null);
        assert((result.mcpCalls[0]?.elapsedMs ?? -1) >= 0);
        if (mode === "empty-output") assert.equal(result.mcpCalls[0]?.textBytes, 0);
        else assert((result.mcpCalls[0]?.textBytes ?? 0) > 0);
        assert.equal(result.turns, 2);
        assert.equal(result.output, "Finished fixture lookup.");
        assert(result.usage.tokens.total > 0);
        assert.equal(result.toolErrors, mode === "tool-error" ? 1 : 0);
        if (mode !== "empty-output") assert.match(requests[1] ?? "", mode === "tool-error" ? /fixture failure/ : /fixture value/);
      }
      const request = z.object({ tools: z.array(z.string()), systemPrompt: z.string() }).parse(JSON.parse(await readFile(join(outputDir, "request.json"), "utf8")));
      assert.deepEqual(request.tools, mode === "empty-output" ? ["get_schema", "execute"] : ["lookup"]);
      assert.equal(request.systemPrompt, `${matrix.systemPrompt}\nCurrent working directory: ${process.cwd()}\n`);
      const inference = z.object({ max_tokens: z.number().optional(), max_completion_tokens: z.number().optional() }).parse(JSON.parse(requests[0] ?? "null"));
      assert.equal(inference.max_tokens ?? inference.max_completion_tokens, 50);
      await assert.rejects(runEval({ matrix, model, server, prompt: "Again", outputDir, runtime }), /already contains evidence/);
    } finally {
      await mcp.close();
      http.closeAllConnections();
      await new Promise<void>((done) => http.close(() => done()));
      await rm(directory, { recursive: true, force: true });
    }
  });
}
