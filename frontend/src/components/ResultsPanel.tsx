import { useEffect, useState } from "react";
import { listResults } from "../api";
import type { BenchmarkResult } from "../types";
import { ScorePill } from "./BenchmarksPanel";

export function ResultsPanel() {
  const [rows, setRows] = useState<BenchmarkResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listResults(100)
      .then(setRows)
      .catch((e) => setError(String(e)));
  }, []);

  if (error) return <div className="error">{error}</div>;
  if (rows === null) return <div className="empty">Loading…</div>;
  if (rows.length === 0) return <div className="empty">No results yet — run a benchmark first.</div>;

  return (
    <table data-testid="results-table">
      <thead>
        <tr>
          <th>When</th>
          <th>Benchmark</th>
          <th>Score</th>
          <th>Duration</th>
          <th>Tokens (p+c)</th>
          <th>Response (head)</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.run_id}>
            <td className="mono">{new Date(r.started_at).toLocaleString()}</td>
            <td>{r.benchmark}</td>
            <td><ScorePill score={r.score} /></td>
            <td className="mono">{r.duration_ms}ms</td>
            <td className="mono">{r.prompt_tokens}+{r.completion_tokens}</td>
            <td className="muted">{r.response.slice(0, 80)}{r.response.length > 80 ? "…" : ""}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
