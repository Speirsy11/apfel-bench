import { describe, expect, it } from "vitest";
import { parseSSE } from "../src/sse";

function makeStream(chunks: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const c of chunks) controller.enqueue(c);
      controller.close();
    },
  });
}

function sseResponse(chunks: Uint8Array[]): Response {
  return new Response(makeStream(chunks), {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

function bytes(s: string): Uint8Array {
  return new TextEncoder().encode(s);
}

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const x of gen) out.push(x);
  return out;
}

describe("parseSSE", () => {
  it("parses a single complete event", async () => {
    const events = await collect(
      parseSSE(sseResponse([bytes('data: {"x":1}\n\n')])),
    );
    expect(events).toEqual([{ x: 1 }]);
  });

  it("skips the [DONE] sentinel", async () => {
    const events = await collect(
      parseSSE(sseResponse([bytes('data: {"x":1}\n\ndata: [DONE]\n\n')])),
    );
    expect(events).toEqual([{ x: 1 }]);
  });

  it("handles an event split across multiple byte chunks", async () => {
    const events = await collect(
      parseSSE(
        sseResponse([
          bytes('data: {"x"'),
          bytes(':"split"}\n\n'),
        ]),
      ),
    );
    expect(events).toEqual([{ x: "split" }]);
  });

  it("handles multiple events in one chunk", async () => {
    const events = await collect(
      parseSSE(sseResponse([bytes('data: {"i":0}\n\ndata: {"i":1}\n\n')])),
    );
    expect(events).toEqual([{ i: 0 }, { i: 1 }]);
  });

  it("handles trailing data without a final blank line", async () => {
    const events = await collect(
      parseSSE(sseResponse([bytes('data: {"i":2}')])),
    );
    expect(events).toEqual([{ i: 2 }]);
  });

  it("skips non-JSON data lines silently", async () => {
    const events = await collect(
      parseSSE(
        sseResponse([
          bytes("data: not json\n\ndata: {\"ok\":true}\n\n"),
        ]),
      ),
    );
    expect(events).toEqual([{ ok: true }]);
  });

  it("yields nothing for an empty body", async () => {
    const events = await collect(parseSSE(sseResponse([])));
    expect(events).toEqual([]);
  });

  it("parses CRLF event boundaries (SSE spec)", async () => {
    // sse-starlette emits `\r\n\r\n` between events. The parser must accept
    // CRLF, not just LF, otherwise no events are ever yielded.
    const events = await collect(
      parseSSE(
        sseResponse([
          bytes('event: message\r\ndata: {"i":0}\r\n\r\n'),
          bytes('event: message\r\ndata: {"i":1}\r\n\r\n'),
        ]),
      ),
    );
    expect(events).toEqual([{ i: 0 }, { i: 1 }]);
  });

  it("handles bare-CR line endings", async () => {
    // Some legacy servers send `\r\r` as a separator. Accept it too.
    const events = await collect(
      parseSSE(sseResponse([bytes('data: {"x":1}\r\r')])),
    );
    expect(events).toEqual([{ x: 1 }]);
  });
});
