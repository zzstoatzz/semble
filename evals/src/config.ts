import { readFile } from "node:fs/promises";
import { z } from "zod";

const name = z.string().regex(/^[a-zA-Z0-9_-]+$/);
export const ModelCase = z.strictObject({
  name,
  provider: z.string().min(1),
  id: z.string().min(1),
  thinking: z.enum(["off", "minimal", "low", "medium", "high", "xhigh", "max"]),
});
export type ModelCase = z.infer<typeof ModelCase>;

export const ServerCase = z.strictObject({
  name,
  url: z.url(),
  headersFromEnv: z.record(z.string(), z.string().min(1)).default({}),
});
export type ServerCase = z.infer<typeof ServerCase>;

export const EvalMatrix = z.strictObject({
  models: z.array(ModelCase).min(1),
  defaultModels: z.array(name).min(1).optional(),
  servers: z.array(ServerCase).min(1),
  repetitions: z.number().int().positive().default(1),
  concurrency: z.number().int().positive().default(1),
  timeoutSeconds: z.number().positive().default(120),
  maxTurns: z.number().int().positive().default(20),
  maxOutputTokens: z.number().int().positive().default(2048),
  judge: ModelCase.default({ name: "judge", provider: "anthropic", id: "claude-haiku-4-5", thinking: "off" }),
  systemPrompt: z.string().min(1),
}).superRefine((matrix, ctx) => {
  for (const selected of matrix.defaultModels ?? []) {
    if (!matrix.models.some((model) => model.name === selected)) {
      ctx.addIssue({ code: "custom", path: ["defaultModels"], message: `Unknown default model: ${selected}` });
    }
  }
  for (const key of ["models", "servers"] as const) {
    if (new Set(matrix[key].map((entry) => entry.name)).size !== matrix[key].length) {
      ctx.addIssue({ code: "custom", path: [key], message: "Names must be unique" });
    }
  }
});
export type EvalMatrix = z.infer<typeof EvalMatrix>;

export async function readMatrix(path: string) {
  return EvalMatrix.parse(JSON.parse(await readFile(path, "utf8")));
}

export function serverHeaders(server: ServerCase) {
  const headers: Record<string, string> = {};
  for (const [header, variable] of Object.entries(server.headersFromEnv)) {
    const value = process.env[variable];
    if (!value) throw new Error(`${server.name}: missing environment variable ${variable}`);
    headers[header] = value;
  }
  return headers;
}
