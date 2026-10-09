import { ArrowLeft, Download, Github, Linkedin, Mail, MapPin, Phone, RefreshCw, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Avatar, Chip, SkillChips, Spinner, formatDate } from "../components/ui";
import api, { downloadResume, errorMessage } from "../lib/api";

function externalUrl(value) {
  return value.startsWith("http") ? value : `https://${value}`;
}

function Section({ title, children }) {
  return (
    <section className="card">
      <h2 className="mb-3 font-semibold">{title}</h2>
      {children}
    </section>
  );
}

export default function CandidateDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [c, setCandidate] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .get(`/candidates/${id}`)
      .then((r) => setCandidate(r.data))
      .catch((e) => {
        toast.error(errorMessage(e));
        navigate("/candidates");
      });
  }, [id, navigate]);

  const reparse = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/candidates/${id}/reparse`);
      setCandidate(data);
      toast.success(`Re-parsed with ${data.parse_method === "llm" ? "Gemini" : "heuristics"}`);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete ${c.name}? This also removes their resume file.`)) return;
    try {
      await api.delete(`/candidates/${id}`);
      toast.success("Candidate deleted");
      navigate("/candidates");
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  if (!c) return <Spinner />;

  const contacts = [
    c.email && { icon: Mail, text: c.email, href: `mailto:${c.email}` },
    c.phone && { icon: Phone, text: c.phone, href: `tel:${c.phone.replace(/\s/g, "")}` },
    c.location && { icon: MapPin, text: c.location },
    c.linkedin && { icon: Linkedin, text: "LinkedIn", href: externalUrl(c.linkedin) },
    c.github && { icon: Github, text: "GitHub", href: externalUrl(c.github) },
  ].filter(Boolean);

  return (
    <div className="space-y-5">
      <Link to="/candidates" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} /> All candidates
      </Link>

      <div className="card flex flex-col gap-4 md:flex-row md:items-start">
        <Avatar name={c.name} />
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{c.name}</h1>
          <p className="text-slate-600">
            {[c.current_title, c.current_company].filter(Boolean).join(" @ ") || "Title not detected"}
            {c.years_experience != null && <span className="text-slate-400"> · {c.years_experience} yrs</span>}
          </p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-sm text-slate-600">
            {contacts.map(({ icon: Icon, text, href }) => (
              <span key={text} className="inline-flex items-center gap-1.5">
                <Icon size={15} className="text-slate-400" />
                {href ? <a href={href} target="_blank" rel="noreferrer" className="hover:text-indigo-600">{text}</a> : text}
              </span>
            ))}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Chip tone="accent">{c.parse_method === "llm" ? "Parsed by Gemini" : "Parsed by heuristics"}</Chip>
            <Chip>Source: {c.source}</Chip>
            <Chip>Added {formatDate(c.created_at)}</Chip>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" onClick={() => downloadResume(c.id, c.original_filename).catch((e) => toast.error(errorMessage(e)))}>
            <Download size={16} /> Resume
          </button>
          <button className="btn-secondary" onClick={reparse} disabled={busy}>
            <RefreshCw size={16} className={busy ? "animate-spin" : ""} /> Re-parse
          </button>
          <button className="btn-danger" onClick={remove}>
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {c.summary && (
        <Section title="Summary">
          <p className="text-sm leading-relaxed text-slate-700">{c.summary}</p>
        </Section>
      )}

      <Section title={`Skills (${c.skills.length})`}>
        {c.skills.length ? <SkillChips skills={c.skills} /> : <p className="text-sm text-slate-500">No skills detected.</p>}
      </Section>

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="Experience">
          {c.experience.length === 0 ? (
            <p className="text-sm text-slate-500">
              Not extracted. {c.parse_method !== "llm" && "Detailed history needs Gemini parsing."}
            </p>
          ) : (
            <ol className="space-y-4 border-l border-slate-200 pl-4">
              {c.experience.map((e, i) => (
                <li key={i}>
                  <div className="font-medium">{e.title}</div>
                  <div className="text-sm text-slate-600">{e.company}</div>
                  <div className="text-xs text-slate-400">{[e.start, e.end].filter(Boolean).join(" – ")}</div>
                  {e.highlights?.length > 0 && (
                    <ul className="mt-1 list-disc pl-4 text-sm text-slate-600">
                      {e.highlights.map((h, j) => <li key={j}>{h}</li>)}
                    </ul>
                  )}
                </li>
              ))}
            </ol>
          )}
        </Section>

        <Section title="Education">
          {c.education.length === 0 ? (
            <p className="text-sm text-slate-500">Not extracted.</p>
          ) : (
            <ul className="space-y-3">
              {c.education.map((e, i) => (
                <li key={i}>
                  <div className="font-medium">{e.degree}</div>
                  <div className="text-sm text-slate-600">{e.institution}{e.year && ` · ${e.year}`}</div>
                </li>
              ))}
            </ul>
          )}
        </Section>
      </div>

      <details className="card">
        <summary className="cursor-pointer font-semibold">Extracted resume text</summary>
        <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-600">{c.resume_text}</pre>
      </details>
    </div>
  );
}
