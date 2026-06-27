import { useEffect, useState } from "react";
import { listResults, runBenchmark } from "../api";
import type { BenchmarkMeta, BenchmarkResult } from "../types";
import { ScorePill } from "./BenchmarksPanel";
import { ResultsTable } from "./ResultsTable";

/**
 * Per-benchmark detail view: description, a Run button, a score-over-runs
 * trend sparkline, and the benchmark's own run history (filtered via
 * `GET /api/results?benchmark=<slug>`). Reached by clicking a card in the
 * Benchmarks grid; `onBack` returns to it.
 */
export function BenchmarkDetail({
  benchmark,
  onBack,
  onRanResult,
}: {
  benchmark: BenchmarkMeta;
  onBack: () => void;
  onRanResult?: () => void;
}) {
  const [history, setHistory] = useState<BenchmarkResult[] | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [benchmark.slug]);

  async function refresh() {
    try {
      setHistory(await listResults(50, benchmark.slug));
    } catch (e) {
      setError(String(e));
    }
  }

  async function run() {
    setRunning(true);
    setError(null);
    try {
      const result = await runBenchmark(benchmark.slug);
      setHistory((prev) => [result, ...(prev ?? [])]);
      onRanResult?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(false);
    }
  }

  const latest = history?.[0];

  return (
    <div className="detail">
      <button className="btn-back" onClick={onBack} data-testid="detail-back">
        ← All benchmarks
      </button>

      <div className="detail-head">
        <div className="detail-title">
          <h2>{benchmark.name}</h2>
          <span className="slug">{benchmark.slug}</span>
        </div>
        <button
          className="btn btn-primary"
          disabled={running}
          onClick={run}
          data-testid={`run-${benchmark.slug}`}
        >
          {running ? "Running…" : latest ? "Re-run" : "Run"}
        </button>
      </div>
      <p className="detail-desc">{benchmark.description}</p>

      {error && <div className="error">{error}</div>}

      {latest && (
        <div className="detail-summary">
          <span className="metric"><span className="metric-k">latest</span><ScorePill score={latest.score} /></span>
          <span className="metric"><span className="metric-k">latency</span>{latest.duration_ms}ms</span>
          <span className="metric"><span className="metric-k">runs</span>{history?.length ?? 0}</span>
        </div>
      )}

      {history && history.length > 1 && <TrendChart history={history} />}

      <div className="table-wrap">
        {history === null ? (
          <div className="empty">Loading…</div>
        ) : history.length === 0 ? (
          <div className="empty">Not run yet — hit Run to record the first result.</div>
        ) : (
          <>
            <div className="table-head">
              <span className="table-count">{history.length} run{history.length === 1 ? "" : "s"}</span>
              <span className="table-hint">Select a row for prompt, response &amp; latency</span>
            </div>
            <ResultsTable rows={history} showBenchmarkColumn={false} />
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Score-per-run sparkline, newest on the right. Same zero-dep inline-SVG
 * style as LatencyChart; scores are a fixed 0–1 scale so bars are directly
 * comparable across runs.
 */
function TrendChart({ history }: { history: BenchmarkResult[] }) {
  // history is newest-first; render oldest -> newest left-to-right.
  const scores = [...history].reverse().map((r) => r.score);
  const W = 320, H = 80, padX = 4, padY = 6;
  const innerW = W - 2 * padX, innerH = H - 2 * padY;
  const bw = innerW / scores.length;
  const yFor = (v: number) => padY + innerH - v * innerH; // score is 0..1

  return (
    <div className="latency-chart trend-chart" data-testid="trend-chart">
      <svg width={W} height={H} role="img" aria-label="score per run">
        {scores.map((v, i) => {
          const x = padX + i * bw;
          const y = yFor(v);
          const h = padY + innerH - y;
          const cls = v === 1 ? "var(--green)" : v === 0 ? "var(--red)" : "var(--accent)";
          return <rect key={i} x={x + 0.5} y={y} width={Math.max(bw - 1, 1)} height={Math.max(h, 1)} fill={cls} opacity="0.85" />;
        })}
        <line x1={padX} y1={yFor(1)} x2={W - padX} y2={yFor(1)} stroke="var(--green)" strokeDasharray="3 2" opacity="0.4" />
      </svg>
      <div className="latency-stats">
        <span><b>score trend</b> oldest → newest ({scores.length} runs)</span>
      </div>
    </div>
  );
}
