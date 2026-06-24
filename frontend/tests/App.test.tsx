import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../src/App";

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Default mocks: one smoke benchmark, no results
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (url === "/api/benchmarks") {
          return new Response(JSON.stringify([{ slug: "smoke", name: "Smoke", description: "d" }]), { status: 200 });
        }
        if (url.startsWith("/api/results")) {
          return new Response("[]", { status: 200 });
        }
        if (url === "/api/chat/sessions") {
          return new Response("[]", { status: 200 });
        }
        return new Response("{}", { status: 200 });
      }),
    );
  });

  it("renders the header and default tab", async () => {
    render(<App />);
    expect(screen.getByText(/apfel/)).toBeInTheDocument();
    expect(await screen.findByTestId("run-smoke")).toBeInTheDocument();
  });

  it("switches tabs when clicked", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByTestId("run-smoke");
    await user.click(screen.getByTestId("tab-results"));
    expect(screen.getByText(/no results yet/i)).toBeInTheDocument();
  });

  it("clicking Run triggers a benchmark run and shows the score", async () => {
    let ranSlug: string | null = null;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url === "/api/benchmarks") {
          return new Response(JSON.stringify([{ slug: "smoke", name: "Smoke", description: "d" }]), { status: 200 });
        }
        if (url.startsWith("/api/results")) {
          return new Response("[]", { status: 200 });
        }
        if (init?.method === "POST" && url.endsWith("/run")) {
          ranSlug = url.split("/").slice(-2, -1)[0];
          return new Response(
            JSON.stringify({
              benchmark: "smoke",
              score: 1.0,
              duration_ms: 420,
              prompt_tokens: 3,
              completion_tokens: 1,
              response: "pong",
              started_at: "2026-01-01T00:00:00",
              finished_at: "2026-01-01T00:00:01",
              expected: "pong",
              prompt: "say pong",
              ttft_ms: null,
              metadata: {},
              run_id: "abc",
            }),
            { status: 200 },
          );
        }
        return new Response("{}", { status: 200 });
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    const runBtn = await screen.findByTestId("run-smoke");
    await user.click(runBtn);
    expect(ranSlug).toBe("smoke");
    expect(await screen.findByText(/1\.00/)).toBeInTheDocument();
  });
});
