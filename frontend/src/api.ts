import type { BenchmarkMeta, BenchmarkResult, ChatMessage } from "./types";
import { parseSSE } from "./sse";

const BASE = ""; // Vite dev proxy sends /api to the FastAPI backend.

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export async function listBenchmarks(): Promise<BenchmarkMeta[]> {
  return jsonOrThrow<BenchmarkMeta[]>(await fetch(`${BASE}/api/benchmarks`));
}

export async function listResults(limit = 50): Promise<BenchmarkResult[]> {
  return jsonOrThrow<BenchmarkResult[]>(
    await fetch(`${BASE}/api/results?limit=${limit}`),
  );
}

export async function runBenchmark(slug: string): Promise<BenchmarkResult> {
  return jsonOrThrow<BenchmarkResult>(
    await fetch(`${BASE}/api/benchmarks/${slug}/run`, { method: "POST" }),
  );
}

export async function postChat(messages: { role: string; content: string }[]): Promise<Response> {
  return fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
}

/** Events the server can emit on /api/chat/stream. */
export type StreamEvent =
  | { type: "chunk"; content: string }
  | {
      type: "done";
      session_id: string;
      full_response: string;
      finish_reason: string | null;
      ttft_ms: number | null;
      duration_ms: number;
    }
  | { type: "error"; message: string };

/**
 * Open an SSE streaming chat turn with apfel.
 *
 * The caller iterates the returned async generator; each yielded event is a
 * typed `StreamEvent`. The generator's `return()` aborts the underlying
 * fetch so the consumer can cancel mid-stream.
 */
export async function* streamChat(
  messages: ChatMessage[],
  sessionId: string | null,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, messages }),
    signal,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${detail}`);
  }
  for await (const event of parseSSE<StreamEvent>(res)) {
    yield event;
  }
}
