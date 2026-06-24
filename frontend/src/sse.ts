// Parse a Server-Sent Events response body into a stream of typed payloads.
//
// Resilient to:
//  - events split across fetch chunks (the byte boundary is independent
//    of the SSE event boundary)
//  - trailing data after the last \\n\\n
//  - multiple `data:` lines per event (we join them with newlines)
//  - non-JSON data lines (skipped silently)
//
// Yields whatever the server put in the `data:` field, parsed as JSON when
// possible. Use it like:
//
//   for await (const ev of parseSSE(response)) {
//     if (ev.type === "chunk") appendToLastMessage(ev.content)
//   }
//
// Mirrors the Python `sse_decode_bytes` in `apfel_bench/streaming.py` so the
// server and the client agree on framing rules.

export async function* parseSSE<T = unknown>(
  response: Response,
): AsyncGenerator<T> {
  if (!response.body) return;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const flushEvent = (event: string): T | undefined => {
    if (!event.trim()) return undefined;
    const dataLines = event
      .split("\n")
      .filter((l) => l.startsWith("data:"))
      .map((l) => l.slice(5).replace(/^ /, ""));
    if (dataLines.length === 0) return undefined;
    const payload = dataLines.join("\n");
    if (!payload || payload === "[DONE]") return undefined;
    try {
      return JSON.parse(payload) as T;
    } catch {
      return undefined;
    }
  };

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buffer.indexOf("\n\n")) >= 0) {
      const event = buffer.slice(0, idx);
      buffer = buffer.slice(idx + 2);
      const parsed = flushEvent(event);
      if (parsed !== undefined) yield parsed;
    }
  }
  if (buffer.trim()) {
    const parsed = flushEvent(buffer);
    if (parsed !== undefined) yield parsed;
  }
}
