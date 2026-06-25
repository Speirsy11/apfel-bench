import { useEffect, useState } from "react";
import { listResults } from "../api";
import type { BenchmarkResult } from "../types";
import { ScorePill } from "./BenchmarksPanel";
import { LatencyChart } from "./LatencyChart";

export function ResultsPanel() {
  const [rows, setRows] = useState<BenchmarkResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    listResults(100)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (rows === null) return <div className="empty">Loading…</div>;
  if (rows.length === 0) return <div className="empty">No results yet — run a benchmark first.</div>;

  return (
    <div className="table-wrap">
      <div className="table-head">
        <span className="table-count">{rows.length} run{rows.length === 1 ? "" : "s"}</span>
        <span className="table-hint">Select a row for prompt, response &amp; latency</span>
      </div>
      <table data-testid="results-table">
      <thead>
        <tr>
          <th></th>
          <th>When</th>
          <th>Benchmark</th>
          <th>Score</th>
          <th>Duration</th>
          <th>Tokens (p+c)</th>
          <th>Response (head)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => {
          const open = openId === r.run_id;
          return (
            <>
              <tr
                key={r.run_id}
                className={`result-row ${open ? "open" : ""}`}
                onClick={() => setOpenId(open ? null : r.run_id)}
                data-testid="result-row"
              >
                <td className="caret">{open ? "▾" : "▸"}</td>
                <td className="mono">{new Date(r.started_at).toLocaleString()}</td>
                <td>{r.benchmark}</td>
                <td><ScorePill score={r.score} /></td>
                <td className="mono">{r.duration_ms}ms</td>
                <td className="mono">{r.prompt_tokens}+{r.completion_tokens}</td>
                <td className="muted">{r.response.slice(0, 80)}{r.response.length > 80 ? "…" : ""}</td>
              </tr>
              {open && (
                <tr className="detail-row" data-testid="result-detail">
                  <td></td>
                  <td colSpan={6}>
                    <div className="result-detail">
                      {r.metadata?.per_run_ms && r.metadata.per_run_ms.length > 0 && (
                        <LatencyChart
                          perRunMs={r.metadata.per_run_ms}
                          tokensPerSec={r.metadata.tokens_per_sec}
                        />
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
            </>
          );
        })}
      </tbody>
      </table>
    </div>
  );
}
