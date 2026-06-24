import { useState } from "react";
import { BenchmarksPanel } from "./components/BenchmarksPanel";
import { ChatPanel } from "./components/ChatPanel";
import { ResultsPanel } from "./components/ResultsPanel";

type Tab = "benchmarks" | "chat" | "results";

export function App() {
  const [tab, setTab] = useState<Tab>("benchmarks");
  const [resultsTick, setResultsTick] = useState(0);

  return (
    <div className="app">
      <header className="app-header">
        <h1>apfel<span className="dot">·</span>bench</h1>
        <span className="tagline">100% on-device · Apple FoundationModel · {new Date().toLocaleDateString()}</span>
      </header>
      <nav className="tabs" role="tablist">
        <button className={`tab ${tab === "benchmarks" ? "active" : ""}`} onClick={() => setTab("benchmarks")} data-testid="tab-benchmarks">
          Benchmarks
        </button>
        <button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")} data-testid="tab-chat">
          Chat
        </button>
        <button className={`tab ${tab === "results" ? "active" : ""}`} onClick={() => { setTab("results"); setResultsTick((t) => t + 1); }} data-testid="tab-results">
          Results
        </button>
      </nav>
      <main>
        {tab === "benchmarks" && <BenchmarksPanel onRanResult={() => setResultsTick((t) => t + 1)} />}
        {tab === "chat" && <ChatPanel />}
        {tab === "results" && <ResultsPanel key={resultsTick} />}
      </main>
    </div>
  );
}
