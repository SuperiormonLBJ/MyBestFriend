"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getStoredAdminKey, ADMIN_SESSION_KEY } from "@/lib/session-auth";
import { AdminPageHeader } from "@/components/admin-page-header";
import { SectionCard } from "@/components/ui/section-card";
import {
  Play,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  FlaskConical,
  Brain,
  Search,
  Settings2,
} from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
type LLMResult = {
  accuracy: number;
  relevance: number;
  completeness: number;
  confidence: number;
  score: number;
  feedback: string;
};

type RetrievalResult = {
  MRR: number;
  keyword_coverage: number;
};

type EvalResult = {
  llm: LLMResult;
  retrieval: RetrievalResult;
  test_count: number;
  config_snapshot?: Record<string, unknown>;
};

type JobStatus = "idle" | "running" | "done" | "error";

type Job = {
  status: JobStatus;
  started_at?: number;
  finished_at?: number;
  result?: EvalResult;
  error?: string;
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function elapsed(started: number, finished?: number) {
  const secs = Math.round((finished ?? Date.now() / 1000) - started);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function scoreColor(value: number, max: number) {
  const pct = value / max;
  if (pct >= 0.8) return "var(--primary)";
  if (pct >= 0.6) return "#f59e0b";
  return "#ef4444";
}

function scoreBarBg(value: number, max: number) {
  const pct = value / max;
  if (pct >= 0.8) return "bg-[var(--primary)]";
  if (pct >= 0.6) return "bg-amber-500";
  return "bg-red-500";
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------
function MetricBar({
  label,
  value,
  max,
  format,
}: {
  label: string;
  value: number;
  max: number;
  format?: (v: number) => string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  const displayVal = format ? format(value) : value.toFixed(2);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-[var(--foreground-muted)]">{label}</span>
        <span
          className="font-semibold tabular-nums"
          style={{ color: scoreColor(value, max) }}
        >
          {displayVal}
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--border)]">
        <div
          className={`h-full rounded-full transition-all duration-700 ${scoreBarBg(value, max)}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ScoreBadge({ value, max }: { value: number; max: number }) {
  const pct = value / max;
  const color = scoreColor(value, max);
  const ring =
    pct >= 0.8
      ? "ring-[var(--primary)]/40"
      : pct >= 0.6
        ? "ring-amber-500/40"
        : "ring-red-500/40";

  return (
    <div
      className={`flex h-16 w-16 shrink-0 flex-col items-center justify-center rounded-full ring-2 ${ring}`}
      style={{ color }}
    >
      <span className="text-xl font-bold tabular-nums leading-none">
        {value.toFixed(1)}
      </span>
      <span className="text-xs opacity-60">/ {max}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function EvalPage() {
  const [job, setJob] = useState<Job>({ status: "idle" });
  const [jobId, setJobId] = useState<string | null>(null);
  const [ticker, setTicker] = useState(0); // used for elapsed-time re-render
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load last persisted result from Supabase on mount
  useEffect(() => {
    fetch("/api/evaluate/latest", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (data?.status === "done" && data?.result) {
          setJob(data);
        }
      })
      .catch(() => {});
  }, []);

  // Tick every second while running so elapsed time updates live
  useEffect(() => {
    if (job.status !== "running") return;
    const id = setInterval(() => setTicker((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [job.status]);

  const poll = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/evaluate/${id}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: Job = await res.json();
      setJob(data);
      if (data.status === "running") {
        pollRef.current = setTimeout(() => poll(id), 3000);
      }
    } catch (err) {
      setJob((prev) => ({
        ...prev,
        status: "error",
        error: err instanceof Error ? err.message : "Polling failed",
      }));
    }
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  const handleRun = async () => {
    if (pollRef.current) clearTimeout(pollRef.current);
    setJob({ status: "running", started_at: Date.now() / 1000 });
    setJobId(null);
    try {
      const res = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "X-Admin-Key": getStoredAdminKey() },
      });
      if (res.status === 401) {
        sessionStorage.removeItem(ADMIN_SESSION_KEY);
        window.location.href = "/admin";
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setJobId(data.job_id);
      setJob((prev) => ({ ...prev, ...data }));
      pollRef.current = setTimeout(() => poll(data.job_id), 3000);
    } catch (err) {
      setJob({
        status: "error",
        error: err instanceof Error ? err.message : "Failed to start",
      });
    }
  };

  const isRunning = job.status === "running";
  const isDone = job.status === "done";
  const isError = job.status === "error";
  const result = job.result;

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <AdminPageHeader
        title="EVALUATION"
        subtitle="Run the RAG evaluation suite against your test questions."
        actions={
          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning}
            className="flex items-center gap-2 border-2 border-[#000000] bg-[#000000] px-5 py-2.5 font-body text-sm font-bold text-[var(--primary)] hover:bg-[#000000]/80 disabled:opacity-50 transition-colors cursor-pointer"
          >
            {isRunning ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {isRunning ? "Running…" : "Run Evaluation"}
          </button>
        }
      />

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-6">

          {/* Status banner */}
          {isRunning && (
            <div className="flex items-center gap-3 border-2 border-[var(--border)] bg-[var(--primary)]/20 px-4 py-3 font-body text-sm font-semibold text-[var(--foreground)]">
              <RefreshCw className="h-4 w-4 shrink-0 animate-spin text-teal-500" />
              <span>
                Evaluating test questions…{" "}
                {job.started_at && (
                  <span className="opacity-70">
                    {elapsed(job.started_at)} elapsed
                  </span>
                )}
              </span>
            </div>
          )}

          {isError && (
            <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-400">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{job.error ?? "Evaluation failed."}</span>
            </div>
          )}

          {isDone && (
            <div className="flex items-center gap-3 border-2 border-[var(--border)] bg-[var(--primary)]/20 px-4 py-3 font-body text-sm font-semibold text-[var(--foreground)]">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
              <span>
                Evaluation complete —{" "}
                <span className="font-medium">{result?.test_count ?? 0} questions</span>
                {job.started_at && job.finished_at && (
                  <span className="opacity-70">
                    {" "}in {elapsed(job.started_at, job.finished_at)}
                  </span>
                )}
                {!job.started_at && job.finished_at && (
                  <span className="opacity-70">
                    {" "}· last run {new Date(job.finished_at * 1000).toLocaleString()}
                  </span>
                )}
              </span>
            </div>
          )}

          {/* Idle placeholder */}
          {job.status === "idle" && (
            <div className="rounded-xl border border-dashed border-[var(--border)] px-8 py-16 text-center">
              <FlaskConical className="mx-auto mb-3 h-10 w-10 text-teal-400/50" />
              <p className="text-sm font-medium text-[var(--foreground-muted)]">
                No results yet
              </p>
              <p className="mt-1 text-xs text-[var(--foreground-muted)]/60">
                Click <span className="font-medium">Run Evaluation</span> to start
              </p>
            </div>
          )}

          {/* LLM Evaluation */}
          {(isDone || isRunning) && result && (
            <SectionCard
              icon={<Brain className="h-4 w-4 text-violet-400" />}
              title="LLM Evaluation"
              badge={<ScoreBadge value={result.llm.score} max={5} />}
            >
              <div className="space-y-4">
                <MetricBar
                  label="Accuracy"
                  value={result.llm.accuracy}
                  max={5}
                  format={(v) => `${v.toFixed(2)} / 5`}
                />
                <MetricBar
                  label="Relevance"
                  value={result.llm.relevance}
                  max={5}
                  format={(v) => `${v.toFixed(2)} / 5`}
                />
                <MetricBar
                  label="Completeness"
                  value={result.llm.completeness}
                  max={5}
                  format={(v) => `${v.toFixed(2)} / 5`}
                />
                <MetricBar
                  label="Confidence"
                  value={result.llm.confidence}
                  max={5}
                  format={(v) => `${v.toFixed(2)} / 5`}
                />
                {result.llm.feedback && (
                  <p className="mt-2 rounded-lg bg-[var(--background)] px-4 py-3 text-xs italic text-[var(--foreground-muted)]">
                    {result.llm.feedback}
                  </p>
                )}
              </div>
            </SectionCard>
          )}

          {/* Retrieval Metrics */}
          {(isDone || isRunning) && result && (
            <SectionCard
              icon={<Search className="h-4 w-4 text-teal-400" />}
              title="Retrieval Metrics"
            >
              <div className="space-y-4">
                <MetricBar
                  label="Mean Reciprocal Rank (MRR)"
                  value={result.retrieval.MRR}
                  max={1}
                  format={(v) => v.toFixed(3)}
                />
                <MetricBar
                  label="Keyword Coverage"
                  value={result.retrieval.keyword_coverage}
                  max={100}
                  format={(v) => `${v.toFixed(1)}%`}
                />
              </div>
            </SectionCard>
          )}

          {/* Config snapshot */}
          {isDone && result?.config_snapshot && (
            <SectionCard
              icon={<Settings2 className="h-4 w-4 text-neutral-400" />}
              title="Config at time of run"
            >
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs">
                {(["generator_model", "rewrite_model", "reranker_model",
                   "hybrid_search_enabled", "self_check_enabled", "multi_step_enabled"] as string[])
                  .filter((k) => result.config_snapshot![k] !== undefined)
                  .map((k) => (
                    <div key={k} className="flex items-center justify-between gap-2">
                      <span className="text-[var(--foreground-muted)] truncate">{k.replace(/_/g, " ")}</span>
                      <span className="font-mono font-medium text-[var(--foreground)] truncate">
                        {String(result.config_snapshot![k])}
                      </span>
                    </div>
                  ))}
              </div>
            </SectionCard>
          )}

          {/* Job ID footnote */}
          {jobId && (
            <p className="text-center text-xs text-[var(--foreground-muted)]/50">
              Job ID: <code>{jobId}</code>
            </p>
          )}

        </div>
      </div>
    </div>
  );
}
