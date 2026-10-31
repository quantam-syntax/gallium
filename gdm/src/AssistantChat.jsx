import { useEffect, useRef, useState } from "react";
import { apiRequest } from "./api.js";

const staffPrompts = ["What is our MRR?", "Which invoices are overdue?", "What does the Odoo variant cost?", "How many subscriptions are active?"];
const customerPrompts = ["When is my next bill?", "What do I still owe?", "How can I manage my plan?"];

export default function AssistantChat({ role }) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState(null);
  const endRef = useRef(null);
  const prompts = role === "customer" ? customerPrompts : staffPrompts;

  useEffect(() => { if (open) endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" }); }, [messages, open, pending]);
  useEffect(() => {
    setMessages([]);
    setMode(null);
    setDraft("");
    setError("");
  }, [role]);

  async function send(question) {
    const message = question.trim();
    if (!message || pending) return;
    const history = messages.slice(-8).map(({ role: speaker, content }) => ({ role: speaker, content }));
    setMessages((previous) => [...previous, { role: "user", content: message }]);
    setDraft("");
    setError("");
    setPending(true);
    try {
      const response = await apiRequest("/api/assistant/chat", { method: "POST", body: { message, history } });
      setMessages((previous) => [...previous, { role: "assistant", content: response.answer }]);
      setMode(response.mode);
    } catch (failure) {
      setError(failure.message || "The assistant could not reply. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return <div className="assistant-shell">
    {open && <section className="assistant-panel" aria-label="Brightloop assistant">
      <header className="assistant-header">
        <span className="assistant-mark" aria-hidden="true">✦</span>
        <span><strong>Brightloop assistant</strong><small>{mode === "demo" ? "Data-backed demo mode" : mode === "ai" ? "Gemini · live Brightloop data" : "Ask anything about Brightloop"}</small></span>
        <button type="button" aria-label="Close assistant" onClick={() => setOpen(false)}>×</button>
      </header>
      <div className="assistant-conversation" role="log" aria-live="polite">
        {messages.length === 0 && <div className="assistant-welcome"><span>✦</span><h2>How can I help?</h2><p>{role === "customer" ? "Ask anything about your Brightloop account, subscriptions, and invoices." : "Ask about any Brightloop product, workflow, subscription, invoice, payment, or report."}</p></div>}
        {messages.map((item, index) => <div className={`assistant-message assistant-message-${item.role}`} key={index}><span>{item.role === "assistant" ? "✦" : "You"}</span><p>{item.content}</p></div>)}
        {pending && <div className="assistant-thinking"><i /><i /><i /><span>Checking Brightloop data…</span></div>}
        {error && <p className="assistant-error" role="alert">{error}</p>}
        <div ref={endRef} />
      </div>
      {messages.length === 0 && <div className="assistant-prompts">{prompts.map((prompt) => <button type="button" key={prompt} onClick={() => send(prompt)}>{prompt}<span>↗</span></button>)}</div>}
      <form className="assistant-compose" onSubmit={(event) => { event.preventDefault(); send(draft); }}>
        <label className="sr-only" htmlFor="assistant-question">Ask Brightloop assistant</label>
        <input id="assistant-question" value={draft} onChange={(event) => setDraft(event.target.value)} maxLength={1000} placeholder="Ask a question…" disabled={pending} />
        <button type="submit" aria-label="Send question" disabled={pending || !draft.trim()}>↑</button>
      </form>
      <p className="assistant-footnote">Brightloop questions only · Read-only answers</p>
    </section>}
    <button className={`assistant-launcher ${open ? "assistant-launcher-open" : ""}`} type="button" aria-label={open ? "Close Brightloop assistant" : "Open Brightloop assistant"} aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span aria-hidden="true">{open ? "×" : "✦"}</span>{!open && <strong>Ask Brightloop</strong>}
    </button>
  </div>;
}
