"use client";

import { startTransition, useDeferredValue, useState } from "react";

import { fallbackChatPayload } from "@/lib/demo-data";
import { readStoredSession } from "@/lib/session";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const slashCommands = [
  "/today",
  "/score <job_id> <candidate_id>",
  "/draft <job_id> <candidate_id>"
];

function parseSse(raw) {
  return raw
    .split("\n\n")
    .filter((chunk) => chunk.startsWith("data: "))
    .map((chunk) => JSON.parse(chunk.slice(6)));
}

export function ChatWorkspace() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Use /today, /score, or /draft. Admin roles can also run scheduling, assessment, and invoice commands. If the server session is unavailable, the panel falls back to demo payloads."
    }
  ]);
  const [panel, setPanel] = useState(fallbackChatPayload);
  const [input, setInput] = useState("/today");
  const [busy, setBusy] = useState(false);
  const deferredPanel = useDeferredValue(panel);

  const [session] = useState(() => readStoredSession());
  const isAdmin = session.user?.role === "owner" || session.user?.role === "team_admin";
  const commandHints = isAdmin
    ? [...slashCommands, "/screen <job_id> <candidate_id>", "/assess <job_id> <candidate_id>", "/interview <job_id> <candidate_id> <interviewer>", "/invoice <client_id> <amount>"]
    : slashCommands;

  async function handleSubmit(event) {
    event.preventDefault();
    const prompt = input.trim();
    if (!prompt) {
      return;
    }
    setMessages((current) => [...current, { role: "user", content: prompt }]);
    setInput("");
    setBusy(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/agent/chat`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ session_id: "web-chat", message: prompt })
      });
      const text = await response.text();
      const events = response.ok ? parseSse(text) : [];
      if (!response.ok) {
        throw new Error(text || "Chat request failed");
      }
      const assistantText = events
        .filter((item) => item.type === "text")
        .map((item) => item.content)
        .join("\n");
      const render = events.find((item) => item.type === "render") || fallbackChatPayload;
      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: assistantText || "No live SSE payload was returned. Showing demo panel state."
          }
        ]);
        setPanel(render);
      });
    } catch {
      startTransition(() => {
        setMessages((current) => [
          ...current,
          {
            role: "assistant",
            content: "API unavailable. Demo render state is still shown so the workbench layout remains inspectable."
          }
        ]);
        setPanel(fallbackChatPayload);
      });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-layout">
      <section className="chat-thread">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Chat runtime</h2>
            <p className="panel-copy">Shared access path into todo lookup, scoring, and draft generation.</p>
          </div>
          <span className="pill accent">{busy ? "Streaming" : "Idle"}</span>
        </div>
        <div className="message-stream">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={`message ${message.role}`}>
              {message.content}
            </div>
          ))}
        </div>
        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={isAdmin ? "Try /today, /screen job_x candidate_y, or /invoice client_x 120000" : "Try /today, /score job_x candidate_y, or /draft job_x candidate_y"}
          />
          <div className="composer-row">
            <div className="slash-list">
              {commandHints.map((command) => (
                <button
                  key={command}
                  type="button"
                  className="button secondary"
                  onClick={() => setInput(command)}
                >
                  {command}
                </button>
              ))}
            </div>
            <button className="button" type="submit" disabled={busy}>
              {busy ? "Running..." : "Send"}
            </button>
          </div>
        </form>
      </section>
      <aside className="chat-panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Render surface</h2>
            <p className="panel-copy">The inspector switches on the same render types emitted by the API.</p>
          </div>
          <span className="pill">{deferredPanel.render_type}</span>
        </div>
        <div className="render-shell">
          {deferredPanel.render_type === "todo_list" ? (
            (deferredPanel.data?.todos || []).map((item) => (
              <div className="list-row" key={item.title}>
                <div>
                  <div className="eyebrow">{item.type}</div>
                  <div className="row-title">{item.title}</div>
                </div>
                <div className="tiny">{item.link}</div>
                <div>
                  <span className="pill accent">{item.priority}</span>
                </div>
                <div className="tiny">Render card</div>
              </div>
            ))
          ) : (
            <pre className="tiny">{JSON.stringify(deferredPanel.data, null, 2)}</pre>
          )}
        </div>
      </aside>
    </div>
  );
}
