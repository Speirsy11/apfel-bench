import { useEffect, useRef, useState } from "react";
import { postChat } from "../api";
import type { ChatMessage } from "../types";

type Session = { id: string; title: string; updated_at: string };

const STORAGE_KEY = "apfel-bench.chat.session";

export function ChatPanel() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeId, setActiveId] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scroller = useRef<HTMLDivElement | null>(null);

  useEffect(() => { refreshSessions(); }, []);
  useEffect(() => { if (activeId) loadSession(activeId); }, [activeId]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

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
    } catch (e) {
      setError(String(e));
    }
  }

  async function newChat() {
    setActiveId(null);
    setMessages([]);
    localStorage.removeItem(STORAGE_KEY);
  }

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setError(null);
    setSending(true);
    const userMsg: ChatMessage = { role: "user", content: text };
    const next = [...messages, userMsg];
    setMessages([...next, { role: "assistant", content: "" }]);
    try {
      const res = await postChat(next);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `${res.status}`);
      }
      const body = await res.json();
      setMessages([...next, { role: "assistant", content: body.reply }]);
      localStorage.setItem(STORAGE_KEY, body.session_id);
      setActiveId(body.session_id);
      refreshSessions();
    } catch (e) {
      setError(String(e));
      setMessages(next);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-shell">
      <aside className="chat-sessions">
        <h4>Sessions</h4>
        <button className="btn" style={{ width: "100%", marginBottom: 8 }} onClick={newChat} data-testid="new-chat">
          + New chat
        </button>
        {sessions.length === 0 && <div className="muted" style={{ fontSize: 12 }}>No chats yet.</div>}
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`chat-session ${activeId === s.id ? "active" : ""}`}
            onClick={() => { setActiveId(s.id); localStorage.setItem(STORAGE_KEY, s.id); }}
          >
            <span>{s.title || "Untitled"}</span>
            <span className="when">{new Date(s.updated_at).toLocaleString()}</span>
          </div>
        ))}
      </aside>
      <section className="chat-pane">
        <div className="chat-messages" ref={scroller} data-testid="chat-messages">
          {messages.length === 0 && <div className="empty">Say hi to the model.</div>}
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>{m.content}</div>
          ))}
        </div>
        {error && <div className="error" style={{ margin: "0 12px 8px" }}>{error}</div>}
        <div className="chat-input-row">
          <input
            value={input}
            placeholder={sending ? "Thinking…" : "Type a message"}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }}
            disabled={sending}
            data-testid="chat-input"
          />
          <button className="btn btn-primary" onClick={send} disabled={sending || !input.trim()} data-testid="chat-send">
            Send
          </button>
        </div>
      </section>
    </div>
  );
}
