// Pure stats for the latency benchmark chart. TDD: deterministic,
// no DOM. The Results panel just renders what this returns.

export type LatencyStats = {
  runs: number;
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
  min_ms: number;
  max_ms: number;
  total_ms: number;
};

export function summarizeLatency(perRunMs: number[]): LatencyStats {
  if (perRunMs.length === 0) {
    return { runs: 0, mean_ms: 0, p50_ms: 0, p95_ms: 0, min_ms: 0, max_ms: 0, total_ms: 0 };
  }
  const sorted = [...perRunMs].sort((a, b) => a - b);
  const total = sorted.reduce((a, b) => a + b, 0);
  const pick = (q: number) => {
    const i = Math.min(sorted.length - 1, Math.floor(q * (sorted.length - 1)));
    return sorted[i];
  };
  return {
    runs: sorted.length,
    mean_ms: total / sorted.length,
    p50_ms: pick(0.5),
    p95_ms: pick(0.95),
    min_ms: sorted[0],
    max_ms: sorted[sorted.length - 1],
    total_ms: total,
  };
}
