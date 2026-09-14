import { defineTool, type AgentToolResult } from "@earendil-works/pi-coding-agent";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { CallToolResultSchema, type CallToolResult, type Tool } from "@modelcontextprotocol/sdk/types.js";
import { Type } from "typebox";
import { z } from "zod";
import { serverHeaders, type ServerCase } from "./config.js";

export async function connectMcp(server: ServerCase, signal: AbortSignal) {
  const client = new Client({ name: "semble-pi-evals", version: "0.1.0" });
  const transport = new StreamableHTTPClientTransport(new URL(server.url), {
    requestInit: { headers: serverHeaders(server), signal },
  });
  try {
    await client.connect(transport, { signal });
    const inventory: Tool[] = [];
    let cursor: string | undefined;
    const cursors = new Set<string>();
    do {
      const page = await client.listTools({ cursor }, { signal });
      inventory.push(...page.tools);
      cursor = page.nextCursor;
      if (cursor && cursors.has(cursor)) throw new Error("MCP tools/list repeated a cursor");
      if (cursor) cursors.add(cursor);
    } while (cursor);
    if (!inventory.length) throw new Error(`${server.name}: no MCP tools returned`);
    if (new Set(inventory.map((tool) => tool.name)).size !== inventory.length) {
      throw new Error(`${server.name}: duplicate MCP tool names`);
    }
    return { client, inventory };
  } catch (error) {
    await client.close();
    throw error;
  }
}

export function mcpTool(client: Client, tool: Tool) {
  return defineTool({
    name: tool.name,
    label: tool.title ?? tool.name,
    description: tool.description ?? "",
    // MCP owns the JSON Schema. Arguments remain untrusted until parsed below;
    // Pi validates against this unchanged schema before calling execute.
    parameters: Type.Unsafe<unknown>(tool.inputSchema),
    async execute(_id, input, signal): Promise<AgentToolResult<CallToolResult>> {
      const args = z.record(z.string(), z.json()).parse(input);
      const result = CallToolResultSchema.parse(await client.callTool(
        { name: tool.name, arguments: args }, CallToolResultSchema, { signal },
      ));
      // Pi marks thrown tool errors as isError and lets the model recover.
      if (result.isError) throw new Error(JSON.stringify(result));
      const content: AgentToolResult<CallToolResult>["content"] = result.content.map((block) => {
        if (block.type === "text") return { type: "text", text: block.text };
        if (block.type === "image") {
          return { type: "image", mimeType: block.mimeType, data: block.data };
        }
        return { type: "text", text: JSON.stringify(block) };
      });
      if (!content.length && result.structuredContent) {
        content.push({ type: "text", text: JSON.stringify(result.structuredContent) });
      }
      return { content, details: result };
    },
  });
}
