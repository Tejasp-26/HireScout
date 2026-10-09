import { Send, Sparkles, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Avatar } from "../components/ui";
import api, { errorMessage } from "../lib/api";

const SUGGESTIONS = [
  "Who are my strongest Python backend candidates?",
  "Compare the candidates with cloud experience",
  "Who has worked on machine learning in production?",
  "Find someone who could lead a frontend team",
];

const WELCOME = {
  role: "assistant",
  content: "Hi! Ask me about your candidates — I search your talent pool and answer from their profiles.",
  candidates: [],
};

export default function Assistant() {
  const [messages, setMessages] = useState([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    const history = messages.slice(1).map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: message }]);
    setInput("");
    setLoading(true);
    try {
      const { data } = await api.post("/assistant/chat", { message, history });
      setMessages((m) => [...m, { role: "assistant", content: data.answer, candidates: data.candidates }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Sorry, something went wrong: ${errorMessage(e)}`, candidates: [] }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col md:h-[calc(100vh-4rem)]">
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="page-title">AI assistant</h1>
          <p className="page-subtitle">Retrieval-augmented answers grounded in your candidates' resumes.</p>
        </div>
        <button className="btn-secondary" onClick={() => setMessages([WELCOME])}><Trash2 size={16} /> Clear</button>
      </div>

      <div className="card flex-1 space-y-4 overflow-y-auto">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-800"}`}>
              {m.role === "assistant" && (
                <div className="mb-1 flex items-center gap-1 text-xs font-semibold text-indigo-700"><Sparkles size={13} /> HireScout</div>
              )}
              <div className="whitespace-pre-wrap leading-relaxed">{m.content}</div>
              {m.candidates?.length > 0 && (
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {m.candidates.map((c) => (
                    <Link key={c.id} to={`/candidates/${c.id}`} className="flex items-center gap-2 rounded-xl bg-white p-2.5 hover:ring-2 hover:ring-indigo-200">
                      <Avatar name={c.name} />
                      <div className="min-w-0">
                        <div className="truncate font-medium text-slate-900">{c.name}</div>
                        <div className="truncate text-xs text-slate-500">{c.current_title || c.skills.slice(0, 3).join(", ")}</div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && <div className="text-sm text-slate-500">HireScout is thinking...</div>}
        <div ref={bottom} />
      </div>

      {messages.length === 1 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button key={s} onClick={() => send(s)} className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-600 hover:border-indigo-300">
              {s}
            </button>
          ))}
        </div>
      )}

      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(); }}>
        <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about your candidates..." />
        <button className="btn-primary" disabled={loading || !input.trim()} aria-label="Send"><Send size={16} /></button>
      </form>
    </div>
  );
}
