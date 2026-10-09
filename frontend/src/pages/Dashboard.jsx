import { CheckCircle2, UploadCloud, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { EmptyState, Spinner, StatCard } from "../components/ui";
import api from "../lib/api";

// Single-series charts: one hue, recessive grid and axes.
const SERIES = "#4f46e5";
const GRID = "#e2e8f0";
const AXIS = { fontSize: 12, fill: "#64748b" };

function ChartCard({ title, subtitle, children }) {
  return (
    <div className="card">
      <h2 className="font-semibold">{title}</h2>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      <div className="mt-4 h-64">{children}</div>
    </div>
  );
}

function StatusLine({ ok, label, detail }) {
  const Icon = ok ? CheckCircle2 : XCircle;
  return (
    <div className="flex items-start gap-2 text-sm">
      <Icon size={18} className={ok ? "text-emerald-600" : "text-slate-400"} />
      <div>
        <span className="font-medium">{label}</span>
        <span className="text-slate-500"> — {detail}</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/analytics").then((res) => setData(res.data));
  }, []);

  if (!data) return <Spinner />;

  const { totals, system } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">Your talent pool at a glance.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Candidates" value={totals.candidates} />
        <StatCard label="Open jobs" value={totals.jobs} />
        <StatCard label="Added this week" value={totals.added_last_7_days} />
        <StatCard label="Distinct skills" value={totals.unique_skills} />
      </div>

      {totals.candidates === 0 ? (
        <EmptyState
          icon={UploadCloud}
          title="No candidates yet"
          text="Import a few resumes and HireScout will parse them, index them for semantic search, and make them matchable against your jobs."
          action={<Link to="/import" className="btn-primary">Import resumes</Link>}
        />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <ChartCard title="Top skills" subtitle="Number of candidates with each skill">
              <ResponsiveContainer>
                <BarChart data={data.top_skills} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid horizontal={false} stroke={GRID} />
                  <XAxis type="number" allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="skill" width={110} tick={AXIS} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#eef2ff" }} formatter={(v) => [v, "Candidates"]} />
                  <Bar dataKey="count" fill={SERIES} radius={[0, 4, 4, 0]} barSize={14} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Resumes imported" subtitle="Last 30 days">
              <ResponsiveContainer>
                <AreaChart data={data.timeline} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid vertical={false} stroke={GRID} />
                  <XAxis dataKey="date" tick={AXIS} tickFormatter={(d) => d.slice(5)} minTickGap={24} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                  <Tooltip formatter={(v) => [v, "Imported"]} />
                  <Area type="monotone" dataKey="count" stroke={SERIES} strokeWidth={2} fill={SERIES} fillOpacity={0.12} />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>

            <ChartCard title="Experience" subtitle="Candidates by years of experience">
              <ResponsiveContainer>
                <BarChart data={data.experience} margin={{ left: -16, right: 8 }}>
                  <CartesianGrid vertical={false} stroke={GRID} />
                  <XAxis dataKey="bucket" tick={AXIS} axisLine={false} tickLine={false} />
                  <YAxis allowDecimals={false} tick={AXIS} axisLine={false} tickLine={false} />
                  <Tooltip cursor={{ fill: "#eef2ff" }} formatter={(v) => [v, "Candidates"]} />
                  <Bar dataKey="count" fill={SERIES} radius={[4, 4, 0, 0]} barSize={32} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>

            <div className="card space-y-4">
              <h2 className="font-semibold">System status</h2>
              <StatusLine
                ok={system.ai_enabled}
                label="Gemini AI"
                detail={system.ai_enabled ? "parsing, matching and assistant use the LLM" : "add GEMINI_API_KEY to enable"}
              />
              <StatusLine
                ok={system.search_index_ready}
                label="Semantic search"
                detail={system.search_index_ready ? `${system.search_index_size} candidates indexed` : "index is rebuilding..."}
              />
              <StatusLine
                ok={system.drive_configured}
                label="Google Drive import"
                detail={system.drive_configured ? "connected" : "optional — not configured"}
              />
              <div className="border-t border-slate-100 pt-4 text-sm text-slate-600">
                <div>Parsed by AI: <b>{data.parse_methods.llm || 0}</b> · by heuristics: <b>{data.parse_methods.heuristic || 0}</b></div>
                <div>Imports — added: <b>{data.ingestion_status.added || 0}</b> · duplicates: <b>{data.ingestion_status.duplicate || 0}</b> · failed: <b>{data.ingestion_status.failed || 0}</b></div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
