import { describe, expect, it, vi, beforeEach } from "vitest";
import { streamChat, type StreamEvent } from "../src/api";

function sseStream(events: StreamEvent[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      const enc = new TextEncoder();
      for (const ev of events) {
        controller.enqueue(enc.encode(`data: ${JSON.stringify(ev)}\n\n`));
      }
      controller.close();
    },
  });
}

function sseResponse(events: StreamEvent[]): Response {
  return new Response(sseStream(events), {
    status: 200,
    headers: { "content-type": "text/event-stream" },
  });
}

async function collect<T>(gen: AsyncGenerator<T>): Promise<T[]> {
  const out: T[] = [];
  for await (const x of gen) out.push(x);
  return out;
}

describe("streamChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("yields typed chunk and done events from the SSE response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        sseResponse([
          { type: "chunk", content: "Hel" },
          { type: "chunk", content: "lo" },
          { type: "done", session_id: "s1", full_response: "Hello", finish_reason: "stop", ttft_ms: 120, duration_ms: 380 },
        ]),
      ),
    );
    const events = await collect(
      streamChat([{ role: "user", content: "hi" }], null),
    );
    expect(events.length).toBe(3);
    expect(events[0]).toEqual({ type: "chunk", content: "Hel" });
    expect(events[2].type).toBe("done");
    if (events[2].type === "done") {
      expect(events[2].full_response).toBe("Hello");
      expect(events[2].session_id).toBe("s1");
    }
  });

  it("POSTs to /api/chat/stream with session_id and messages", async () => {
    const fetchMock = vi.fn(async () =>
      sseResponse([{ type: "done", session_id: "x", full_response: "", finish_reason: "stop", ttft_ms: null, duration_ms: 0 }]),
    );
    vi.stubGlobal("fetch", fetchMock);
    await collect(
      streamChat(
        [
          { role: "user", content: "hi" },
          { role: "assistant", content: "hello" },
          { role: "user", content: "what's up" },
        ],
        "abc",
      ),
    );
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/chat/stream",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "abc",
          messages: [
            { role: "user", content: "hi" },
            { role: "assistant", content: "hello" },
            { role: "user", content: "what's up" },
          ],
        }),
      }),
    );
  });

  it("throws a useful error when the server returns non-OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "no messages" }), { status: 400 })),
    );
    await expect(
      collect(streamChat([{ role: "user", content: "x" }], null)),
    ).rejects.toThrow(/no messages/);
  });
});
