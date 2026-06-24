import { summarizeLatency, type LatencyStats } from "../latencyStats";

// Tiny inline SVG bar chart. One bar per run, p50/p95 markers as horizontal
// dashed lines. No external chart lib — we want zero deps here.

export function LatencyChart({ perRunMs, tokensPerSec }: { perRunMs: number[]; tokensPerSec?: number }) {
  if (perRunMs.length === 0) return <div className="muted">no runs</div>;
  const s: LatencyStats = summarizeLatency(perRunMs);
  const W = 320, H = 80, padX = 4, padY = 6;
  const innerW = W - 2 * padX, innerH = H - 2 * padY;
  const bw = innerW / s.runs;
  const maxVal = Math.max(s.max_ms, 1);
  const yFor = (v: number) => padY + innerH - (v / maxVal) * innerH;

  return (
    <div className="latency-chart" data-testid="latency-chart">
      <svg width={W} height={H} role="img" aria-label="per-run latency">
        {/* bars */}
        {perRunMs.map((v, i) => {
          const x = padX + i * bw;
          const y = yFor(v);
          const h = padY + innerH - y;
          return <rect key={i} x={x + 0.5} y={y} width={Math.max(bw - 1, 1)} height={h} fill="var(--accent)" opacity="0.85" />;
        })}
        {/* p50 */}
        <line x1={padX} y1={yFor(s.p50_ms)} x2={W - padX} y2={yFor(s.p50_ms)} stroke="var(--green)" strokeDasharray="3 2" />
        <text x={W - padX} y={yFor(s.p50_ms) - 2} textAnchor="end" fontSize="9" fill="var(--green)">p50 {s.p50_ms.toFixed(0)}ms</text>
        {/* p95 */}
        {s.p95_ms > 0 && (
          <>
            <line x1={padX} y1={yFor(s.p95_ms)} x2={W - padX} y2={yFor(s.p95_ms)} stroke="var(--red)" strokeDasharray="3 2" />
            <text x={W - padX} y={yFor(s.p95_ms) - 2} textAnchor="end" fontSize="9" fill="var(--red)">p95 {s.p95_ms.toFixed(0)}ms</text>
          </>
        )}
      </svg>
      <div className="latency-stats">
        <span><b>runs</b> {s.runs}</span>
        <span><b>mean</b> {s.mean_ms.toFixed(0)}ms</span>
        <span><b>min</b> {s.min_ms.toFixed(0)}</span>
        <span><b>max</b> {s.max_ms.toFixed(0)}</span>
        {tokensPerSec !== undefined && <span><b>tok/s</b> {tokensPerSec.toFixed(1)}</span>}
      </div>
    </div>
  );
}
