import { describe, expect, it, vi, beforeEach, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatPanel } from "../src/components/ChatPanel";

// jsdom does not implement HTMLElement#scrollTo; ChatPanel's auto-scroll
// effect would throw without a stub.
beforeAll(() => {
  if (!HTMLElement.prototype.scrollTo) {
    HTMLElement.prototype.scrollTo = function () {};
  }
});

function mockFetchEmpty() {
  return vi.fn(async (url: string) => {
    if (url === "/api/chat/sessions") {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response("{}", { status: 200 });
  });
}

function mockFetchWithSessions() {
  return vi.fn(async (url: string) => {
    if (url === "/api/chat/sessions") {
      return new Response(
        JSON.stringify([
          { id: "s1", title: "First chat", updated_at: "2026-06-25T07:00:00Z" },
          { id: "s2", title: "Second chat", updated_at: "2026-06-25T07:30:00Z" },
        ]),
        { status: 200 },
      );
    }
    if (url === "/api/chat/sessions/s1/messages") {
      return new Response(JSON.stringify([]), { status: 200 });
    }
    return new Response("{}", { status: 200 });
  });
}

describe("ChatPanel drawer", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders the drawer toggle button with a11y attributes", async () => {
    vi.stubGlobal("fetch", mockFetchEmpty());
    render(<ChatPanel />);
    const toggle = await screen.findByTestId("drawer-toggle");
    expect(toggle).toHaveAttribute("aria-label", "Toggle sessions");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("opens the drawer when the toggle is clicked, closes it on a second click", async () => {
    vi.stubGlobal("fetch", mockFetchEmpty());
    const user = userEvent.setup();
    render(<ChatPanel />);
    const toggle = await screen.findByTestId("drawer-toggle");
    const shell = document.querySelector(".chat-shell") as HTMLElement;

    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(shell).not.toHaveClass("drawer-open");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(shell).toHaveClass("drawer-open");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(shell).not.toHaveClass("drawer-open");
  });

  it("closes the drawer when the scrim is clicked", async () => {
    vi.stubGlobal("fetch", mockFetchEmpty());
    const user = userEvent.setup();
    render(<ChatPanel />);
    const toggle = await screen.findByTestId("drawer-toggle");
    const shell = document.querySelector(".chat-shell") as HTMLElement;
    await user.click(toggle);
    expect(shell).toHaveClass("drawer-open");

    const scrim = document.querySelector(".drawer-scrim") as HTMLElement;
    await user.click(scrim);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(shell).not.toHaveClass("drawer-open");
  });

  it("auto-closes the drawer when a session is picked", async () => {
    vi.stubGlobal("fetch", mockFetchWithSessions());
    const user = userEvent.setup();
    render(<ChatPanel />);
    const toggle = await screen.findByTestId("drawer-toggle");

    // Open the drawer.
    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    // Pick a session from the list.
    const session = await screen.findByText("First chat");
    await user.click(session);

    // The drawer should close on its own.
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });

  it("auto-closes the drawer when New chat is started", async () => {
    vi.stubGlobal("fetch", mockFetchEmpty());
    const user = userEvent.setup();
    render(<ChatPanel />);
    const toggle = await screen.findByTestId("drawer-toggle");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    const newChat = screen.getByTestId("new-chat");
    await user.click(newChat);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
