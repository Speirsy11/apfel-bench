import { useEffect, useState } from "react";
import { listBenchmarks, listResults, runBenchmark } from "../api";
import type { BenchmarkMeta, BenchmarkResult } from "../types";

type LastBySlug = Record<string, BenchmarkResult | undefined>;

export function BenchmarksPanel({ onRanResult }: { onRanResult?: () => void }) {
  const [benchmarks, setBenchmarks] = useState<BenchmarkMeta[] | null>(null);
  const [last, setLast] = useState<LastBySlug>({});
  const [running, setRunning] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div>
      {error && <div className="error">{error}</div>}
      <div className="benchmark-list">
        {benchmarks.map((b) => {
          const lr = last[b.slug];
          return (
            <div className="benchmark-card" key={b.slug}>
              <div>
                <h3>{b.name}</h3>
                <p>{b.description}</p>
                <span className="slug">{b.slug}</span>
              </div>
              <div className="actions">
                <button
                  className="btn btn-primary"
                  disabled={running !== null}
                  onClick={() => run(b.slug)}
                  data-testid={`run-${b.slug}`}
                >
                  {running === b.slug ? "Running…" : "Run"}
                </button>
                {lr && (
                  <div className="last-result">
                    Last: <ScorePill score={lr.score} /> · {lr.duration_ms}ms · {lr.prompt_tokens}+{lr.completion_tokens}t
                  </div>
                )}
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
