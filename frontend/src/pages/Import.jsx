import { CheckCircle2, CircleDashed, Copy, FolderSync, Loader2, UploadCloud, XCircle } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";

import { formatDate } from "../components/ui";
import api, { errorMessage } from "../lib/api";

const STATUS = {
  pending: { icon: CircleDashed, className: "text-slate-400", label: "Waiting" },
  uploading: { icon: Loader2, className: "animate-spin text-indigo-600", label: "Parsing..." },
  added: { icon: CheckCircle2, className: "text-emerald-600", label: "Added" },
  duplicate: { icon: Copy, className: "text-amber-600", label: "Duplicate" },
  failed: { icon: XCircle, className: "text-red-600", label: "Failed" },
};

function StatusIcon({ status }) {
  const { icon: Icon, className } = STATUS[status] || STATUS.pending;
  return <Icon size={18} className={className} />;
}

function DriveSync({ onFinished }) {
  const [state, setState] = useState(null);
  const wasRunning = useRef(false);

  const refresh = useCallback(() => api.get("/resumes/drive-sync").then((r) => setState(r.data)), []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!state?.running) {
      if (wasRunning.current) onFinished();
      wasRunning.current = false;
      return;
    }
    wasRunning.current = true;
    const timer = setInterval(refresh, 2000);
    return () => clearInterval(timer);
  }, [state?.running, refresh, onFinished]);

  const start = async () => {
    try {
      const { data } = await api.post("/resumes/drive-sync");
      setState(data);
    } catch (e) {
      toast.error(errorMessage(e));
    }
  };

  if (!state) return null;

  return (
    <div className="card">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 font-semibold"><FolderSync size={18} /> Google Drive folder</h2>
          <p className="text-sm text-slate-500">
            {state.configured
              ? "Import every new PDF from your shared Drive folder."
              : "Optional: set GOOGLE_SERVICE_ACCOUNT_FILE and GOOGLE_DRIVE_FOLDER_ID on the backend to enable."}
          </p>
        </div>
        <button className="btn-primary" onClick={start} disabled={!state.configured || state.running}>
          {state.running ? <><Loader2 size={16} className="animate-spin" /> Syncing...</> : "Sync now"}
        </button>
      </div>

      {(state.running || state.finished_at) && (
        <div className="mt-4 space-y-2">
          {state.total > 0 && (
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div className="h-full bg-indigo-600 transition-all" style={{ width: `${(state.processed / state.total) * 100}%` }} />
            </div>
          )}
          <p className="text-sm text-slate-600">
            {state.processed}/{state.total} processed · {state.added} added · {state.duplicates} duplicates · {state.failed} failed
            {state.finished_at && !state.running && <span className="text-slate-400"> · finished {formatDate(state.finished_at)}</span>}
          </p>
          {state.error && <p className="text-sm text-red-600">{state.error}</p>}
        </div>
      )}
    </div>
  );
}

export default function Import() {
  const [queue, setQueue] = useState([]);
  const [logs, setLogs] = useState([]);
  const running = useRef(false);

  const loadLogs = useCallback(() => api.get("/resumes/logs", { params: { limit: 50 } }).then((r) => setLogs(r.data)), []);

  useEffect(() => {
    loadLogs();
  }, [loadLogs]);

  const processQueue = useCallback(async (items) => {
    // Upload one at a time: each file may take a few seconds to parse with the LLM.
    running.current = true;
    for (const item of items) {
      setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, status: "uploading" } : x)));
      const form = new FormData();
      form.append("file", item.file);
      let update;
      try {
        const { data } = await api.post("/resumes/upload", form);
        update = { status: data.status, detail: data.detail, candidateId: data.candidate_id, name: data.candidate_name };
      } catch (e) {
        update = { status: "failed", detail: errorMessage(e) };
      }
      setQueue((q) => q.map((x) => (x.id === item.id ? { ...x, ...update } : x)));
    }
    running.current = false;
    loadLogs();
  }, [loadLogs]);

  const onDrop = useCallback(
    (accepted, rejected) => {
      if (rejected.length) toast.error(`${rejected.length} file(s) skipped — only PDFs are supported`);
      if (!accepted.length) return;
      if (running.current) {
        toast("Please wait for the current batch to finish");
        return;
      }
      const items = accepted.map((file, i) => ({ id: `${Date.now()}-${i}`, file, status: "pending" }));
      setQueue(items);
      processQueue(items);
    },
    [processQueue]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: true,
  });

  const done = queue.filter((x) => !["pending", "uploading"].includes(x.status)).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="page-title">Import resumes</h1>
        <p className="page-subtitle">Resumes are parsed into structured profiles, deduplicated and indexed for search.</p>
      </div>

      <div
        {...getRootProps()}
        className={`card flex cursor-pointer flex-col items-center border-2 border-dashed py-12 text-center transition ${
          isDragActive ? "border-indigo-500 bg-indigo-50" : "border-slate-300 hover:border-indigo-400"
        }`}
      >
        <input {...getInputProps()} />
        <UploadCloud size={32} className="text-indigo-600" />
        <p className="mt-3 font-semibold">{isDragActive ? "Drop the PDFs here" : "Drag & drop resume PDFs"}</p>
        <p className="text-sm text-slate-500">or click to choose files</p>
      </div>

      {queue.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-semibold">This batch · {done}/{queue.length} done</h2>
          <ul className="divide-y divide-slate-100">
            {queue.map((item) => (
              <li key={item.id} className="flex items-start gap-3 py-2.5 text-sm">
                <StatusIcon status={item.status} />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-medium">{item.file.name}</div>
                  <div className="text-slate-500">
                    {STATUS[item.status].label}
                    {item.name && <> · {item.candidateId ? <Link className="text-indigo-600 hover:underline" to={`/candidates/${item.candidateId}`}>{item.name}</Link> : item.name}</>}
                    {item.detail && <> · {item.detail}</>}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <DriveSync onFinished={loadLogs} />

      <div className="card overflow-x-auto">
        <h2 className="mb-3 font-semibold">Recent imports</h2>
        {logs.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing imported yet.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2 pr-4 font-medium">File</th>
                <th className="py-2 pr-4 font-medium">Candidate</th>
                <th className="py-2 pr-4 font-medium">Status</th>
                <th className="py-2 pr-4 font-medium">Source</th>
                <th className="py-2 font-medium">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map((log) => (
                <tr key={log.id} title={log.detail || ""}>
                  <td className="max-w-[220px] truncate py-2 pr-4">{log.filename}</td>
                  <td className="py-2 pr-4">
                    {log.candidate_id ? <Link className="text-indigo-600 hover:underline" to={`/candidates/${log.candidate_id}`}>{log.candidate_name}</Link> : log.candidate_name || "—"}
                  </td>
                  <td className="py-2 pr-4">
                    <span className="inline-flex items-center gap-1.5"><StatusIcon status={log.status} /> {STATUS[log.status]?.label || log.status}</span>
                  </td>
                  <td className="py-2 pr-4 capitalize">{log.source}</td>
                  <td className="whitespace-nowrap py-2 text-slate-500">{formatDate(log.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
