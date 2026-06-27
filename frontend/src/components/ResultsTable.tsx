import { Fragment, useState } from "react";
import type { BenchmarkResult } from "../types";
import { ScorePill } from "./BenchmarksPanel";
import { LatencyChart } from "./LatencyChart";

/**
 * Expandable table of benchmark runs. Shared by the global Results view
 * (all benchmarks, `showBenchmarkColumn`) and the per-benchmark detail view
 * (single benchmark, column hidden). Each row toggles open to reveal the
 * prompt, response, metadata, and — for the latency benchmark — a per-run
 * latency chart.
 */
export function ResultsTable({
  rows,
  showBenchmarkColumn,
}: {
  rows: BenchmarkResult[];
  showBenchmarkColumn: boolean;
}) {
  const [openId, setOpenId] = useState<string | null>(null);
  const colCount = showBenchmarkColumn ? 6 : 5;

  return (
    <table data-testid="results-table">
      <thead>
        <tr>
          <th></th>
          <th>When</th>
          {showBenchmarkColumn && <th>Benchmark</th>}
          <th>Score</th>
          <th>Duration</th>
          <th>Tokens (p+c)</th>
          <th>Response (head)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const open = openId === r.run_id;
          // metadata is loosely typed (Record<string, unknown>); narrow the
          // two latency-chart fields before handing them to LatencyChart.
          const perRunMs = Array.isArray(r.metadata?.per_run_ms)
            ? (r.metadata.per_run_ms as number[])
            : null;
          const tokensPerSec = typeof r.metadata?.tokens_per_sec === "number"
            ? r.metadata.tokens_per_sec
            : undefined;
          return (
            <Fragment key={r.run_id}>
              <tr
                className={`result-row ${open ? "open" : ""}`}
                onClick={() => setOpenId(open ? null : r.run_id)}
                data-testid="result-row"
              >
                <td className="caret">{open ? "▾" : "▸"}</td>
                <td className="mono">{new Date(r.started_at).toLocaleString()}</td>
                {showBenchmarkColumn && <td>{r.benchmark}</td>}
                <td><ScorePill score={r.score} /></td>
                <td className="mono">{r.duration_ms}ms</td>
                <td className="mono">{r.prompt_tokens}+{r.completion_tokens}</td>
                <td className="muted">{r.response.slice(0, 80)}{r.response.length > 80 ? "…" : ""}</td>
              </tr>
              {open && (
                <tr className="detail-row" data-testid="result-detail">
                  <td></td>
                  <td colSpan={colCount}>
                    <div className="result-detail">
                      {perRunMs && perRunMs.length > 0 && (
                        <LatencyChart perRunMs={perRunMs} tokensPerSec={tokensPerSec} />
                      )}
                      <div className="kv">
                        <div><b>Prompt:</b> <pre className="prompt">{r.prompt}</pre></div>
                        <div><b>Response:</b> <pre className="response">{r.response}</pre></div>
                        {r.metadata && (
                          <div>
                            <b>Metadata:</b>
                            <pre className="metadata">{JSON.stringify(r.metadata, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}
