import { Loader2 } from "lucide-react";
import { Link } from "react-router-dom";

export function Spinner({ label = "Loading..." }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-slate-500">
      <Loader2 size={18} className="animate-spin" /> {label}
    </div>
  );
}

export function EmptyState({ icon: Icon, title, text, action }) {
  return (
    <div className="card flex flex-col items-center py-12 text-center">
      {Icon && (
        <div className="mb-3 rounded-full bg-indigo-50 p-3 text-indigo-600">
          <Icon size={22} />
        </div>
      )}
      <h3 className="font-semibold">{title}</h3>
      {text && <p className="mt-1 max-w-md text-sm text-slate-500">{text}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function StatCard({ label, value, hint }) {
  return (
    <div className="card">
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-3xl font-bold tracking-tight">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-400">{hint}</div>}
    </div>
  );
}

const CHIP_TONES = {
  neutral: "bg-slate-100 text-slate-700",
  good: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  bad: "bg-red-50 text-red-700 ring-1 ring-red-200",
  accent: "bg-indigo-50 text-indigo-700",
};

export function Chip({ children, tone = "neutral" }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${CHIP_TONES[tone]}`}>
      {children}
    </span>
  );
}

export function SkillChips({ skills = [], max, tone }) {
  const shown = max ? skills.slice(0, max) : skills;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((s) => (
        <Chip key={s} tone={tone}>
          {s}
        </Chip>
      ))}
      {max && skills.length > max && <Chip>+{skills.length - max}</Chip>}
    </div>
  );
}

export function Avatar({ name = "?" }) {
  const initials = name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
  return (
    <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-sm font-bold text-indigo-700">
      {initials || "?"}
    </div>
  );
}

export function CandidateRow({ candidate, right }) {
  const c = candidate;
  const subtitle = [c.current_title, c.current_company].filter(Boolean).join(" @ ");
  const meta = [c.location, c.years_experience != null ? `${c.years_experience} yrs exp` : null]
    .filter(Boolean)
    .join(" · ");

  return (
    <Link
      to={`/candidates/${c.id}`}
      className="card flex flex-col gap-3 transition hover:border-indigo-300 hover:shadow-md sm:flex-row sm:items-center"
    >
      <Avatar name={c.name} />
      <div className="min-w-0 flex-1">
        <div className="font-semibold">{c.name}</div>
        <div className="truncate text-sm text-slate-600">{subtitle || "Title not detected"}</div>
        {meta && <div className="text-xs text-slate-400">{meta}</div>}
        <div className="mt-2">
          <SkillChips skills={c.skills} max={6} />
        </div>
      </div>
      {right}
    </Link>
  );
}

export function formatDate(value) {
  if (!value) return "";
  // SQLite returns timestamps without a timezone; they are stored as UTC.
  const iso = /(Z|[+-]\d\d:\d\d)$/.test(value) ? value : `${value}Z`;
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
