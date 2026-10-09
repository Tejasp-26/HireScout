import { Briefcase, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Link, useNavigate } from "react-router-dom";

import { EmptyState, SkillChips, Spinner, formatDate } from "../components/ui";
import api, { errorMessage } from "../lib/api";

function NewJobForm({ onCancel }) {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const { data } = await api.post("/jobs", { title, description });
      toast.success(`Extracted ${data.required_skills.length} required skills`);
      navigate(`/jobs/${data.id}`);
    } catch (err) {
      toast.error(errorMessage(err));
      setSaving(false);
    }
  };

  return (
    <form onSubmit={submit} className="card space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-semibold">New job</h2>
        <button type="button" onClick={onCancel} className="text-slate-400 hover:text-slate-700" aria-label="Close"><X size={18} /></button>
      </div>
      <div>
        <label className="label" htmlFor="title">Job title</label>
        <input id="title" className="input" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Senior Backend Engineer" required minLength={2} />
      </div>
      <div>
        <label className="label" htmlFor="desc">Job description</label>
        <textarea
          id="desc"
          className="input min-h-[200px]"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Paste the full job description. HireScout will extract required skills, nice-to-haves and minimum experience."
          required
          minLength={20}
        />
      </div>
      <button className="btn-primary" disabled={saving}>
        {saving ? "Analysing job description..." : "Create & find matches"}
      </button>
    </form>
  );
}

export default function Jobs() {
  const [jobs, setJobs] = useState(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    api.get("/jobs").then((r) => setJobs(r.data));
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="page-title">Jobs & matching</h1>
          <p className="page-subtitle">Paste a job description and get a ranked shortlist with skill gaps.</p>
        </div>
        {!showForm && (
          <button className="btn-primary" onClick={() => setShowForm(true)}><Plus size={16} /> New job</button>
        )}
      </div>

      {showForm && <NewJobForm onCancel={() => setShowForm(false)} />}

      {!jobs ? (
        <Spinner />
      ) : jobs.length === 0 ? (
        !showForm && (
          <EmptyState
            icon={Briefcase}
            title="No jobs yet"
            text="Create a job from a job description to rank your candidates against it."
            action={<button className="btn-primary" onClick={() => setShowForm(true)}><Plus size={16} /> New job</button>}
          />
        )
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {jobs.map((job) => (
            <Link key={job.id} to={`/jobs/${job.id}`} className="card transition hover:border-indigo-300 hover:shadow-md">
              <div className="font-semibold">{job.title}</div>
              <div className="mb-3 text-xs text-slate-400">
                Created {formatDate(job.created_at)}
                {job.min_years_experience != null && ` · ${job.min_years_experience}+ yrs`}
              </div>
              <SkillChips skills={job.required_skills} max={8} tone="accent" />
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
