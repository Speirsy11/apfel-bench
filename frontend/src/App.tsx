import { useState } from "react";
import { BenchmarksPanel } from "./components/BenchmarksPanel";
import { ChatPanel } from "./components/ChatPanel";
import { ResultsPanel } from "./components/ResultsPanel";

type Tab = "benchmarks" | "chat" | "results";

const VIEWS: Record<Tab, { title: string; subtitle: string }> = {
  benchmarks: { title: "Benchmarks", subtitle: "Run the suite against the on-device model" },
  chat: { title: "Chat", subtitle: "Stream responses with time-to-first-token" },
  results: { title: "Results", subtitle: "History, scores, and latency breakdowns" },
};

export function App() {
  const [tab, setTab] = useState<Tab>("benchmarks");
  const [resultsTick, setResultsTick] = useState(0);

  const nav: { id: Tab; label: string; icon: JSX.Element }[] = [
    { id: "benchmarks", label: "Benchmarks", icon: <IconGauge /> },
    { id: "chat", label: "Chat", icon: <IconChat /> },
    { id: "results", label: "Results", icon: <IconChart /> },
  ];

  const view = VIEWS[tab];

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            <AppleMark />
          </div>
          <div className="brand-text">
            <span className="brand-name">apfel<span className="dot">·</span>bench</span>
            <span className="brand-sub">on-device LLM lab</span>
          </div>
        </div>

        <nav className="nav" role="tablist" aria-label="Primary">
          {nav.map((n) => (
            <button
              key={n.id}
              role="tab"
              aria-selected={tab === n.id}
              className={`nav-item ${tab === n.id ? "active" : ""}`}
              onClick={() => {
                setTab(n.id);
                if (n.id === "results") setResultsTick((t) => t + 1);
              }}
              data-testid={`tab-${n.id}`}
            >
              <span className="nav-icon">{n.icon}</span>
              <span className="nav-label">{n.label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="status-chip">
            <span className="status-dot" />
            <span>100% on-device</span>
          </div>
          <span className="sidebar-meta">Apple FoundationModel</span>
        </div>
      </aside>

      <div className="main-col">
        <header className="topbar">
          <div className="topbar-title">
            <h1>{view.title}</h1>
            <p>{view.subtitle}</p>
          </div>
          <div className="topbar-meta">
            <span className="pill-soft">No cloud · no API keys</span>
            <span className="topbar-date">{new Date().toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}</span>
          </div>
        </header>

        <main className="content">
          {tab === "benchmarks" && <BenchmarksPanel onRanResult={() => setResultsTick((t) => t + 1)} />}
          {tab === "chat" && <ChatPanel />}
          {tab === "results" && <ResultsPanel key={resultsTick} />}
        </main>
      </div>
    </div>
  );
}

/* ---------- inline icons (no deps) ---------- */

function AppleMark() {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
      <path d="M17.05 12.04c-.02-2.3 1.88-3.4 1.96-3.46-1.07-1.56-2.73-1.78-3.32-1.8-1.41-.14-2.76.83-3.48.83-.72 0-1.83-.81-3.01-.79-1.55.02-2.98.9-3.78 2.29-1.61 2.8-.41 6.94 1.16 9.21.77 1.11 1.69 2.36 2.89 2.31 1.16-.05 1.6-.75 3-.75 1.4 0 1.79.75 3.01.72 1.24-.02 2.03-1.13 2.79-2.25.88-1.29 1.24-2.54 1.26-2.6-.03-.01-2.42-.93-2.44-3.71zM14.77 5.3c.64-.78 1.07-1.86.95-2.94-.92.04-2.04.61-2.7 1.39-.59.69-1.11 1.79-.97 2.85 1.03.08 2.08-.52 2.72-1.3z" />
    </svg>
  );
}

function IconGauge() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 13a3 3 0 0 0 3-3" />
      <path d="M3.5 19a9 9 0 1 1 17 0" />
      <path d="M12 10 9 7" />
    </svg>
  );
}

function IconChat() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 11.5a8.5 8.5 0 0 1-12.3 7.6L3 21l1.9-5.7A8.5 8.5 0 1 1 21 11.5z" />
    </svg>
  );
}

function IconChart() {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v18h18" />
      <rect x="7" y="11" width="3" height="6" rx="0.5" />
      <rect x="13" y="7" width="3" height="10" rx="0.5" />
    </svg>
  );
}
