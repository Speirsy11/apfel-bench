import { describe, expect, it, vi, beforeEach } from "vitest";
import { listBenchmarks, listResults, runBenchmark } from "../src/api";

describe("api client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("listBenchmarks fetches /api/benchmarks and parses the JSON", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ slug: "smoke", name: "Smoke", description: "..." }]), {
        status: 200,
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await listBenchmarks();
    expect(result).toEqual([{ slug: "smoke", name: "Smoke", description: "..." }]);
    expect(fetchMock).toHaveBeenCalledWith("/api/benchmarks");
  });

  it("listResults appends a limit query parameter", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await listResults(10);
    expect(fetchMock).toHaveBeenCalledWith("/api/results?limit=10");
  });

  it("listResults appends a benchmark filter when given", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await listResults(50, "smoke");
    expect(fetchMock).toHaveBeenCalledWith("/api/results?limit=50&benchmark=smoke");
  });

  it("runBenchmark POSTs to /api/benchmarks/{slug}/run", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ benchmark: "smoke", score: 1.0 }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const result = await runBenchmark("smoke");
    expect(result.score).toBe(1.0);
    expect(fetchMock).toHaveBeenCalledWith("/api/benchmarks/smoke/run", { method: "POST" });
  });

  it("throws a useful error when the server returns non-OK", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "unknown benchmark: 'nope'" }), { status: 404 }),
      ),
    );
    await expect(runBenchmark("nope")).rejects.toThrow(/unknown benchmark/);
  });
});
