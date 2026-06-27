import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BenchmarksPanel } from "../src/components/BenchmarksPanel";

function row(over: Partial<Record<string, unknown>> = {}) {
  return {
    benchmark: "factual_qa",
    score: 0.8,
    duration_ms: 420,
    prompt_tokens: 30,
    completion_tokens: 12,
    response: "Paris is the capital of France.",
    started_at: "2026-06-24T10:00:00",
    finished_at: "2026-06-24T10:00:01",
    expected: "Paris",
    prompt: "What is the capital of France?",
    ttft_ms: null,
    metadata: {},
    run_id: "r1",
    ...over,
  };
}

describe("BenchmarkDetail drill-down", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("opens a benchmark's detail, fetches its filtered history, and Back returns to the grid", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        calls.push(url);
        if (url === "/api/benchmarks") {
          return new Response(
            JSON.stringify([{ slug: "factual_qa", name: "Factual QA", description: "10 MCQs" }]),
            { status: 200 },
          );
        }
        // grid prefetch (no benchmark filter) -> empty so the card shows "not run yet"
        if (url === "/api/results?limit=50") {
          return new Response("[]", { status: 200 });
        }
        // per-benchmark history
        if (url.includes("benchmark=factual_qa")) {
          return new Response(JSON.stringify([row(), row({ run_id: "r2", score: 0.7 })]), { status: 200 });
        }
        return new Response("{}", { status: 200 });
      }),
    );

    const user = userEvent.setup();
    render(<BenchmarksPanel />);

    const card = await screen.findByTestId("bench-card-factual_qa");
    await user.click(card);

    // Detail view: description + filtered history table is shown.
    expect(await screen.findByText("10 MCQs")).toBeInTheDocument();
    const table = await screen.findByTestId("results-table");
    expect(within(table).getAllByTestId("result-row")).toHaveLength(2);
    // The filter endpoint was actually hit.
    expect(calls.some((u) => u.includes("benchmark=factual_qa"))).toBe(true);

    // Back returns to the grid.
    await user.click(screen.getByTestId("detail-back"));
    expect(await screen.findByTestId("bench-card-factual_qa")).toBeInTheDocument();
  });

  it("clicking Run on a card does not navigate into the detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url === "/api/benchmarks") {
          return new Response(
            JSON.stringify([{ slug: "factual_qa", name: "Factual QA", description: "10 MCQs" }]),
            { status: 200 },
          );
        }
        if (init?.method === "POST" && url.endsWith("/run")) {
          return new Response(JSON.stringify(row({ score: 1.0 })), { status: 200 });
        }
        if (url.startsWith("/api/results")) {
          return new Response("[]", { status: 200 });
        }
        return new Response("{}", { status: 200 });
      }),
    );

    const user = userEvent.setup();
    render(<BenchmarksPanel />);

    const runBtn = await screen.findByTestId("run-factual_qa");
    await user.click(runBtn);

    // Still on the grid (description hidden inside the card lives there too, so
    // assert via the score appearing on the card, not the detail back button).
    expect(await screen.findByText(/1\.00/)).toBeInTheDocument();
    expect(screen.queryByTestId("detail-back")).not.toBeInTheDocument();
  });
});
