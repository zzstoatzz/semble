import { lookup } from "node:dns/promises";
import { get } from "node:https";

export function publicReadingAddress(address: string) {
  if (address.includes(":")) return /^[23][0-9a-f]{3}:/i.test(address);
  const [a = 0, b = 0] = address.split(".").map(Number);
  return a > 0 && a < 224 && ![10, 127].includes(a) && !(a === 169 && b === 254) &&
    !(a === 172 && b >= 16 && b <= 31) && !(a === 192 && (b === 168 || b === 0)) &&
    !(a === 100 && b >= 64 && b <= 127) && !(a === 198 && (b === 18 || b === 19));
}

// Pin the validated DNS address, including on redirects; candidate URLs are untrusted.
export async function readRecommendationSource(value: string, redirects = 0): Promise<{ url: string; text: string; truncated: boolean }> {
  const url = new URL(value);
  if (url.protocol !== "https:" || url.username || url.password || (url.port && url.port !== "443")) throw new Error("Only public HTTPS reading sources are supported");
  const addresses = await lookup(url.hostname, { all: true });
  if (!addresses.length || addresses.some((entry) => !publicReadingAddress(entry.address))) throw new Error("Non-public reading source address");
  const address = addresses[0];
  if (!address) throw new Error("No source address");
  const response = await new Promise<{ body: string; location?: string; status: number }>((resolve, reject) => {
    const request = get(url, { agent: false, family: address.family,
      lookup: (_hostname, _options, callback) => callback(null, address.address, address.family),
      headers: { Accept: "text/html,text/plain", "User-Agent": "Semble-eval/1.0" },
      signal: AbortSignal.timeout(12_000),
    }, (response) => {
      const chunks: Buffer[] = [];
      let size = 0;
      response.on("data", (chunk: Buffer) => {
        size += chunk.length;
        if (size > 512_000) request.destroy(new Error("Reading source exceeds byte budget"));
        else chunks.push(chunk);
      });
      response.on("end", () => resolve({ body: Buffer.concat(chunks).toString("utf8"), location: response.headers.location, status: response.statusCode ?? 0 }));
      response.on("error", reject);
    });
    request.on("error", reject);
  });
  if (response.status >= 300 && response.status < 400 && response.location) {
    if (redirects >= 3) throw new Error("Too many source redirects");
    return readRecommendationSource(new URL(response.location, url).href, redirects + 1);
  }
  if (response.status !== 200) throw new Error(`Reading source HTTP ${response.status}`);
  const article = response.body.match(/<(?:article|main)\b[^>]*>([\s\S]*?)<\/(?:article|main)>/i)?.[1] ?? response.body;
  const text = article.replace(/<(script|style|nav|header|footer)\b[^>]*>[\s\S]*?<\/\1>/gi, " ")
    .replace(/<[^>]+>/g, " ").replace(/&nbsp;/g, " ").replace(/&amp;/g, "&")
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/\s+/g, " ").trim();
  return { url: url.href, text: text.slice(0, 16000), truncated: text.length > 16000 };
}
