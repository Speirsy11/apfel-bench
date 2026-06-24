import { describe, expect, it } from "vitest";
import { summarizeLatency } from "../src/latencyStats";

describe("summarizeLatency", () => {
  it("returns zeros for empty input", () => {
    expect(summarizeLatency([])).toEqual({
      runs: 0,
      mean_ms: 0,
      p50_ms: 0,
      p95_ms: 0,
      min_ms: 0,
      max_ms: 0,
      total_ms: 0,
    });
  });

  it("computes mean/min/max/total", () => {
    const s = summarizeLatency([100, 200, 300]);
    expect(s.runs).toBe(3);
    expect(s.min_ms).toBe(100);
    expect(s.max_ms).toBe(300);
    expect(s.mean_ms).toBe(200);
    expect(s.total_ms).toBe(600);
  });

  it("picks the median for p50 and the near-max for p95", () => {
    // 1..20: p50 should land near 10, p95 near 19
    const s = summarizeLatency(Array.from({ length: 20 }, (_, i) => i + 1));
    expect(s.p50_ms).toBe(10); // floor(0.5 * 19) = 9 → sorted[9] = 10
    expect(s.p95_ms).toBe(19); // floor(0.95 * 19) = 18 → sorted[18] = 19
  });

  it("does not mutate the input array", () => {
    const arr = [300, 100, 200];
    summarizeLatency(arr);
    expect(arr).toEqual([300, 100, 200]);
  });
});
