import { useEffect, useRef, useState } from "react";
import { streamChat, type StreamEvent } from "../api";
import type { ChatMessage } from "../types";

type Session = { id: string; title: string; updated_at: string };

const STORAGE_KEY = "apfel-…sion";

export function ChatPanel() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [streaming, setStreaming] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const scroller = useRef<HTMLDivElement | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => { refreshSessions(); }, []);
  useEffect(() => { if (activeId) loadSession(activeId); }, [activeId]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages, streaming]);

  // Close the mobile drawer when a session is picked or a new chat is started.
  useEffect(() => { setDrawerOpen(false); }, [activeId]);

  async function refreshSessions() {
    try {
      const r = await fetch("/api/chat/sessions");
      if (!r.ok) throw new Error(`${r.status}`);
      setSessions(await r.json());
    } catch (e) {
      setError(String(e));
    }
  }

  async function loadSession(id: string) {
    try {
      const r = await fetch(`/api/chat/sessions/${id}/messages`);
      if (!r.ok) throw new Error(`${r.status}`);
      const data: { role: string; content: string }[] = await r.json();
      setMessages(data.map((m) => ({ role: m.role as ChatMessage["role"], content: m.content })));
      setStreaming("");
    } catch (e) {
      setError(String(e));
    }
  }

  function newChat() {
    abortRef.current?.abort();
    setActiveId(null);
    setMessages([]);
    setStreaming("");
    localStorage.removeItem(STORAGE_KEY);
  }

  function pickSession(id: string) {
    abortRef.current?.abort();
    setActiveId(id);
    setStreaming("");
    localStorage.setItem(STORAGE_KEY, id);
  }

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setError(null);
    setSending(true);
    setStreaming("");

    const userMsg: ChatMessage = { role: "user", content: text };
    const base = [...messages, userMsg];
    setMessages([...base, { role: "assistant", content: "" }]);

    abortRef.current = new AbortController();
    let acc = "";
    try {
      for await (const ev of streamChat(base, activeId, abortRef.current.signal)) {
        if (ev.type === "chunk") {
          acc += ev.content;
          setStreaming(acc);
        } else if (ev.type === "done") {
          const finalAssistant: ChatMessage = { role: "assistant", content: ev.full_response };
          setMessages([...base, finalAssistant]);
          setStreaming("");
          if (!activeId) {
            localStorage.setItem(STORAGE_KEY, ev.session_id);
            setActiveId(ev.session_id);
          }
          refreshSessions();
        } else if (ev.type === "error") {
          throw new Error(ev.message);
        }
      }
    } catch (e) {
      setError(String(e));
      // Roll back the empty assistant placeholder
      setMessages(base);
      setStreaming("");
    } finally {
      setSending(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  return (
    <div className={`chat-shell ${drawerOpen ? "drawer-open" : ""}`}>
      <div
        className="drawer-scrim"
        onClick={() => setDrawerOpen(false)}
        aria-hidden="true"
      />
      <aside className="chat-sessions" aria-label="Chat sessions">
        <h4>Sessions</h4>
        <button className="btn" style={{ width: "100%", marginBottom: 8 }} onClick={newChat} data-testid="new-chat">
          + New chat
        </button>
        {sessions.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No chats yet.</div>}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`chat-session ${activeId === s.id ? "active" : ""}`}
            onClick={() => pickSession(s.id)}
          >
            <span>{s.title || "Untitled"}</span>
            <span className="when">{new Date(s.updated_at).toLocaleString()}</span>
          </div>
        ))}
      </aside>
      <section className="chat-pane">
        <div className="chat-messages" ref={scroller} data-testid="chat-messages">
          {messages.length === 0 && <div className="empty">Say hi to the model.</div>}
          {messages.map((m, i) => {
            const isStreamingAssistant = streaming && i === messages.length - 1 && m.role === "assistant";
            return (
              <div key={i} className={`chat-msg ${m.role}`}>
                {isStreamingAssistant ? streaming : m.content}
                {isStreamingAssistant && <span className="streaming-caret"> ▍</span>}
              </div>
            );
          })}
        </div>
        {error && <div className="error" style={{ margin: "0 12px 8px" }}>{error}</div>}
        <div className="chat-input-row">
          <button
            className="btn drawer-toggle"
            onClick={() => setDrawerOpen((o) => !o)}
            aria-label="Toggle sessions"
            aria-expanded={drawerOpen}
            data-testid="drawer-toggle"
          >
            ☰
          </button>
          <input
            value={input}
            placeholder={sending ? "Streaming…" : "Type a message"}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            disabled={sending}
            data-testid="chat-input"
          />
          {sending ? (
            <button className="btn" onClick={cancel} data-testid="chat-cancel">Stop</button>
          ) : (
            <button className="btn btn-primary" onClick={send} disabled={!input.trim()} data-testid="chat-send">
              Send
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
