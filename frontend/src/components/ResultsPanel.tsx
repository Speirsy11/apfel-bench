import { useEffect, useState } from "react";
import { listResults } from "../api";
import type { BenchmarkResult } from "../types";
import { ResultsTable } from "./ResultsTable";

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
    <div className="table-wrap">
      <div className="table-head">
        <span className="table-count">{rows.length} run{rows.length === 1 ? "" : "s"} across every benchmark</span>
        <span className="table-hint">Select a row for prompt, response &amp; latency</span>
      </div>
      <ResultsTable rows={rows} showBenchmarkColumn />
    </div>
  );
}
