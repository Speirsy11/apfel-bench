import { useEffect, useState } from "react";
import { listBenchmarks, listResults, runBenchmark } from "../api";
import type { BenchmarkMeta, BenchmarkResult } from "../types";
import { BenchmarkDetail } from "./BenchmarkDetail";

type LastBySlug = Record<string, BenchmarkResult | undefined>;

export function BenchmarksPanel({ onRanResult }: { onRanResult?: () => void }) {
  const [benchmarks, setBenchmarks] = useState<BenchmarkMeta[] | null>(null);
  const [last, setLast] = useState<LastBySlug>({});
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    try {
      const [bs, results] = await Promise.all([listBenchmarks(), listResults(50)]);
      setBenchmarks(bs);
      const byslug: LastBySlug = {};
      for (const r of results) {
        if (!byslug[r.benchmark]) byslug[r.benchmark] = r;
      }
      setLast(byslug);
    } catch (e) {
      setError(String(e));
    }
  }

  async function run(slug: string) {
    setRunning(slug);
    setError(null);
    try {
      const result = await runBenchmark(slug);
      setLast((prev) => ({ ...prev, [slug]: result }));
      onRanResult?.();
    } catch (e) {
      setError(String(e));
    } finally {
      setRunning(null);
    }
  }

  if (benchmarks === null) return <div className="empty">Loading…</div>;
  if (benchmarks.length === 0) {
    return <div className="empty">No benchmarks registered. Add one under <code>backend/apfel_bench/benchmarks/</code> and import it in <code>benchmarks/__init__.py</code>.</div>;
  }

  const selectedBench = selected ? benchmarks.find((b) => b.slug === selected) : undefined;
  if (selectedBench) {
    return (
      <BenchmarkDetail
        benchmark={selectedBench}
        onBack={() => {
          setSelected(null);
          // Pull the latest scores back into the grid after viewing/running.
          refresh();
        }}
        onRanResult={onRanResult}
      />
    );
  }

  return (
    <div>
      {error && <div className="error">{error}</div>}
      <div className="benchmark-list">
        {benchmarks.map((b) => {
          const lr = last[b.slug];
          const isRunning = running === b.slug;
          return (
            <div
              className={`benchmark-card is-clickable ${isRunning ? "is-running" : ""}`}
              key={b.slug}
              role="button"
              tabIndex={0}
              onClick={() => setSelected(b.slug)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  setSelected(b.slug);
                }
              }}
              data-testid={`bench-card-${b.slug}`}
            >
              <div className="bc-main">
                <div className="bc-head">
                  <h3>{b.name}</h3>
                  <span className="slug">{b.slug}</span>
                </div>
                <p>{b.description}</p>
                <div className="bc-metrics">
                  {lr ? (
                    <>
                      <ScorePill score={lr.score} />
                      <span className="metric"><span className="metric-k">latency</span>{lr.duration_ms}ms</span>
                      <span className="metric"><span className="metric-k">tokens</span>{lr.prompt_tokens}+{lr.completion_tokens}</span>
                    </>
                  ) : (
                    <span className="metric metric-empty">not run yet</span>
                  )}
                </div>
                <span className="bc-history">View history →</span>
              </div>
              <div className="actions">
                <button
                  className="btn btn-primary"
                  disabled={running !== null}
                  onClick={(e) => {
                    e.stopPropagation();
                    run(b.slug);
                  }}
                  data-testid={`run-${b.slug}`}
                >
                  {isRunning ? "Running…" : lr ? "Re-run" : "Run"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function ScorePill({ score }: { score: number }) {
  const cls = score === 1 ? "score-1" : score === 0 ? "score-0" : "score-mid";
  return <span className={`score-pill ${cls}`}>{score.toFixed(2)}</span>;
}
