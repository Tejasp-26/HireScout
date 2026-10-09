import { ArrowLeft, Pencil, Sparkles, Trash2, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate, useParams } from "react-router-dom";

import { Avatar, EmptyState, SkillChips, Spinner } from "../components/ui";
import api, { errorMessage } from "../lib/api";

const SIGNAL_LABELS = { skills: "Required skills", semantic: "Profile similarity", experience: "Experience", nice: "Nice-to-haves" };

function scoreTone(score) {
  if (score >= 75) return "bg-emerald-600";
  if (score >= 50) return "bg-indigo-600";
  return "bg-slate-400";
}

function RequirementsEditor({ job, onSaved, onCancel }) {
  const [required, setRequired] = useState(job.required_skills.join(", "));
  const [nice, setNice] = useState(job.nice_to_have_skills.join(", "));
  const [years, setYears] = useState(job.min_years_experience ?? "");

  const split = (s) => s.split(",").map((x) => x.trim()).filter(Boolean);

  const save = async () => {
    try {
      const { data } = await api.patch(`/jobs/${job.id}`, {
        required_skills: split(required),
        nice_to_have_skills: split(nice),
        min_years_experience: years === "" ? null : Number(years),
      });
      onSaved(data);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="label">Required skills (comma-separated)</label>
        <input className="input" value={required} onChange={(e) => setRequired(e.target.value)} />
      </div>
      <div>
        <label className="label">Nice-to-have skills</label>
        <input className="input" value={nice} onChange={(e) => setNice(e.target.value)} />
      </div>
      <div className="max-w-[200px]">
        <label className="label">Minimum years</label>
        <input className="input" type="number" min="0" step="0.5" value={years} onChange={(e) => setYears(e.target.value)} />
      </div>
      <div className="flex gap-2">
        <button className="btn-primary" onClick={save}>Save & re-rank</button>
        <button className="btn-secondary" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}

function MatchCard({ rank, match }) {
  const c = match.candidate;
  return (
    <div className="card">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex items-start gap-3 sm:w-1/3">
          <span className="mt-2.5 w-6 text-sm font-semibold text-slate-400">#{rank}</span>
          <Avatar name={c.name} />
          <div className="min-w-0">
            <Link to={`/candidates/${c.id}`} className="font-semibold hover:text-indigo-600">{c.name}</Link>
            <div className="truncate text-sm text-slate-600">{c.current_title || "Title not detected"}</div>
            <div className="text-xs text-slate-400">{c.years_experience != null ? `${c.years_experience} yrs exp` : "Experience unknown"}</div>
          </div>
        </div>

        <div className="flex-1 space-y-2.5">
          {match.matched_skills.length > 0 && (
            <div><span className="mr-2 text-xs font-medium text-slate-500">Has</span><SkillChips skills={match.matched_skills} tone="good" /></div>
          )}
          {match.missing_skills.length > 0 && (
            <div><span className="mr-2 text-xs font-medium text-slate-500">Missing</span><SkillChips skills={match.missing_skills} tone="bad" /></div>
          )}
          {match.nice_to_have_matched.length > 0 && (
            <div><span className="mr-2 text-xs font-medium text-slate-500">Bonus</span><SkillChips skills={match.nice_to_have_matched} tone="accent" /></div>
          )}
          {match.rationale && (
            <p className="flex gap-2 rounded-xl bg-indigo-50 p-3 text-sm text-indigo-900">
              <Sparkles size={16} className="mt-0.5 shrink-0" /> {match.rationale}
            </p>
          )}
        </div>

        <div className="sm:w-44">
          <div className="flex items-baseline justify-between">
            <span className="text-3xl font-bold">{match.score}</span>
            <span className="text-xs text-slate-400">match score</span>
          </div>
          <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className={`h-full ${scoreTone(match.score)}`} style={{ width: `${match.score}%` }} />
          </div>
          <dl className="mt-2 space-y-0.5 text-xs text-slate-500">
            {Object.entries(match.breakdown).map(([k, v]) => (
              <div key={k} className="flex justify-between"><dt>{SIGNAL_LABELS[k]}</dt><dd className="font-medium text-slate-700">{v}%</dd></div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  );
}

export default function JobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [job, setJob] = useState(null);
  const [matches, setMatches] = useState(null);
  const [editing, setEditing] = useState(false);
  const [explaining, setExplaining] = useState(false);

  const loadMatches = useCallback(
    (explain = 0) => api.get(`/jobs/${id}/matches`, { params: { limit: 25, explain } }).then((r) => setMatches(r.data)),
    [id]
  );

  useEffect(() => {
    api.get(`/jobs/${id}`).then((r) => setJob(r.data)).catch(() => navigate("/jobs"));
    loadMatches();
  }, [id, navigate, loadMatches]);

  const explain = async () => {
    setExplaining(true);
    try {
      await loadMatches(5);
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setExplaining(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete the job "${job.title}"?`)) return;
    await api.delete(`/jobs/${id}`);
    navigate("/jobs");
  };

  if (!job) return <Spinner />;

  return (
    <div className="space-y-5">
      <Link to="/jobs" className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-800">
        <ArrowLeft size={16} /> All jobs
      </Link>

      <div className="card space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-2xl font-bold">{job.title}</h1>
            <p className="text-sm text-slate-500">
              Requirements extracted by {job.extraction_method === "llm" ? "Gemini" : "keyword rules"}
              {job.min_years_experience != null && ` · ${job.min_years_experience}+ years`}
            </p>
          </div>
          <div className="flex gap-2">
            {!editing && <button className="btn-secondary" onClick={() => setEditing(true)}><Pencil size={16} /> Edit requirements</button>}
            <button className="btn-danger" onClick={remove} aria-label="Delete job"><Trash2 size={16} /></button>
          </div>
        </div>

        {editing ? (
          <RequirementsEditor
            job={job}
            onCancel={() => setEditing(false)}
            onSaved={(updated) => {
              setJob(updated);
              setEditing(false);
              setMatches(null);
              loadMatches();
            }}
          />
        ) : (
          <div className="space-y-2">
            <div><div className="mb-1 text-xs font-medium uppercase text-slate-500">Required</div><SkillChips skills={job.required_skills} tone="accent" /></div>
            {job.nice_to_have_skills.length > 0 && (
              <div><div className="mb-1 text-xs font-medium uppercase text-slate-500">Nice to have</div><SkillChips skills={job.nice_to_have_skills} /></div>
            )}
          </div>
        )}

        <details>
          <summary className="cursor-pointer text-sm text-slate-500">Show job description</summary>
          <p className="mt-2 whitespace-pre-wrap text-sm text-slate-700">{job.description}</p>
        </details>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <h2 className="text-lg font-semibold">Best matches</h2>
        <button className="btn-secondary" onClick={explain} disabled={explaining || !matches?.length}>
          <Sparkles size={16} className={explaining ? "animate-pulse" : ""} />
          {explaining ? "Asking Gemini..." : "Explain top 5 with AI"}
        </button>
      </div>

      {!matches ? (
        <Spinner label="Ranking candidates..." />
      ) : matches.length === 0 ? (
        <EmptyState icon={Users} title="No candidates to rank" text="Import resumes first, then come back to this job." />
      ) : (
        <div className="space-y-3">
          {matches.map((m, i) => <MatchCard key={m.candidate.id} rank={i + 1} match={m} />)}
        </div>
      )}
    </div>
  );
}
