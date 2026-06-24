import type { BenchmarkMeta, BenchmarkResult } from "./types";

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
