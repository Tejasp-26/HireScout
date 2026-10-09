import { Search, Sparkles, Users } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { CandidateRow, EmptyState, Spinner } from "../components/ui";
import api, { errorMessage } from "../lib/api";

const PAGE_SIZE = 20;

export default function Candidates() {
  const [mode, setMode] = useState("keyword"); // keyword | semantic
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(1);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (mode === "semantic" && submitted.trim().length < 2) {
      setResult({ items: [], total: 0 });
      return;
    }
    setLoading(true);
    const request =
      mode === "keyword"
        ? api.get("/candidates", { params: { q: submitted, page, page_size: PAGE_SIZE } }).then((r) => r.data)
        : api.get("/search", { params: { q: submitted, limit: 20 } }).then((r) => ({
            items: r.data.map((h) => ({ ...h.candidate, similarity: h.similarity })),
            total: r.data.length,
          }));
    request
      .then(setResult)
      .catch((e) => toast.error(errorMessage(e)))
      .finally(() => setLoading(false));
  }, [mode, submitted, page]);

  const onSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSubmitted(query);
  };

  const switchMode = (next) => {
    setMode(next);
    setPage(1);
    setSubmitted(query);
  };

  const pages = result ? Math.max(1, Math.ceil(result.total / PAGE_SIZE)) : 1;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Candidates</h1>
        <p className="page-subtitle">
          Filter by keyword, or describe who you need and let semantic search find them.
        </p>
      </div>

      <form onSubmit={onSubmit} className="card space-y-3">
        <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm">
          {[
            ["keyword", "Keyword", Search],
            ["semantic", "Semantic (AI)", Sparkles],
          ].map(([value, label, Icon]) => (
            <button
              type="button"
              key={value}
              onClick={() => switchMode(value)}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 font-medium ${
                mode === value ? "bg-white text-indigo-700 shadow-sm" : "text-slate-600"
              }`}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            className="input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              mode === "keyword"
                ? "Name, title, company, location or skill..."
                : 'e.g. "backend engineer with streaming data experience"'
            }
          />
          <button className="btn-primary" type="submit">Search</button>
        </div>
      </form>

      {loading || !result ? (
        <Spinner />
      ) : result.items.length === 0 ? (
        <EmptyState
          icon={Users}
          title={submitted ? "No matching candidates" : mode === "semantic" ? "Describe the candidate you need" : "No candidates yet"}
          text={!submitted && mode === "keyword" ? "Import resumes to build your talent pool." : undefined}
          action={!submitted && mode === "keyword" ? <Link to="/import" className="btn-primary">Import resumes</Link> : undefined}
        />
      ) : (
        <>
          <p className="text-sm text-slate-500">{result.total} candidate{result.total === 1 ? "" : "s"}</p>
          <div className="space-y-3">
            {result.items.map((c) => (
              <CandidateRow
                key={c.id}
                candidate={c}
                right={
                  c.similarity != null && (
                    <div className="text-right text-sm">
                      <div className="font-semibold text-indigo-700">{Math.round(c.similarity * 100)}%</div>
                      <div className="text-xs text-slate-400">similarity</div>
                    </div>
                  )
                }
              />
            ))}
          </div>
          {mode === "keyword" && pages > 1 && (
            <div className="flex items-center justify-center gap-4">
              <button className="btn-secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
              <span className="text-sm text-slate-500">Page {page} of {pages}</span>
              <button className="btn-secondary" disabled={page === pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
