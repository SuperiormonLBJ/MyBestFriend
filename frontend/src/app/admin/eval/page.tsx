"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { getStoredAdminKey } from "@/lib/session-auth";
import { AdminPageHeader } from "@/components/admin-page-header";
import { useAdminWrite } from "@/contexts/admin-write-context";
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
  Database,
  Network,
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

type MultiAgentEvalResult = {
  agent_routing_accuracy: number;
  agent_context_redundancy_ratio: number;
  per_agent_mrr: Record<string, number>;
  synthesis_faithfulness: number;
  parallel_efficiency: number;
  total_questions: number;
};

type MultiAgentJob = {
  status: JobStatus;
  started_at?: number;
  finished_at?: number;
  result?: MultiAgentEvalResult;
  error?: string;
};

type EvalRow = {
  question: string;
  ground_truth: string;
  category: string;
  keywords: string[];
  expected_agents: string[];
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
  const { ensureCanModify, markWriteUnauthenticated } = useAdminWrite();
  const [job, setJob] = useState<Job>({ status: "idle" });
  const [jobId, setJobId] = useState<string | null>(null);
  const [ticker, setTicker] = useState(0); // used for elapsed-time re-render
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [activeTab, setActiveTab] = useState<"run" | "multi_agent" | "dataset">("run");
  const [maJob, setMaJob] = useState<MultiAgentJob>({ status: "idle" });
  const [maJobId, setMaJobId] = useState<string | null>(null);
  const maPollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [dataset, setDataset] = useState<EvalRow[]>([]);
  const [datasetLoading, setDatasetLoading] = useState(false);
  const [datasetError, setDatasetError] = useState<string | null>(null);
  const [datasetDirty, setDatasetDirty] = useState(false);
  const [datasetInfo, setDatasetInfo] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [generateCountInput, setGenerateCountInput] = useState("20");

  const clampGenerateN = (raw: string): number => {
    const n = Number.parseInt(raw, 10);
    if (!Number.isFinite(n)) return 20;
    return Math.min(200, Math.max(1, n));
  };

  const normalizeGenerateCountInput = () => {
    setGenerateCountInput(String(clampGenerateN(generateCountInput)));
  };

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

  // Load last persisted multi-agent result from Supabase on mount
  useEffect(() => {
    fetch("/api/evaluate/multi-agent/latest", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (data?.status === "done" && data?.result) {
          setMaJob(data);
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
      if (maPollRef.current) clearTimeout(maPollRef.current);
    };
  }, []);

  const pollMa = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/evaluate/${id}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: MultiAgentJob = await res.json();
      setMaJob(data);
      if (data.status === "running") {
        maPollRef.current = setTimeout(() => pollMa(id), 3000);
      }
    } catch (err) {
      setMaJob((prev) => ({
        ...prev,
        status: "error",
        error: err instanceof Error ? err.message : "Polling failed",
      }));
    }
  }, []);

  const loadDataset = useCallback(async () => {
    setDatasetLoading(true);
    setDatasetError(null);
    try {
      const res = await fetch("/api/eval/dataset", { cache: "no-store" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      const data: EvalRow[] = await res.json();
      setDataset(data);
      setDatasetDirty(false);
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to load dataset"
      );
    } finally {
      setDatasetLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDataset();
  }, [loadDataset]);

  const handleCellChange = (
    index: number,
    field: keyof EvalRow,
    value: string
  ) => {
    setDataset((prev) => {
      const next = [...prev];
      const row = { ...next[index] };
      if (field === "keywords") {
        row.keywords = value
          .split(",")
          .map((k) => k.trim())
          .filter(Boolean);
      } else if (field === "expected_agents") {
        row.expected_agents = value
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean);
      } else if (field === "category") {
        row.category = value;
      } else if (field === "question") {
        row.question = value;
      } else if (field === "ground_truth") {
        row.ground_truth = value;
      }
      next[index] = row;
      return next;
    });
    setDatasetDirty(true);
  };

  const handleAddRow = () => {
    setDataset((prev) => [
      {
        question: "",
        ground_truth: "",
        category: "general",
        keywords: [],
        expected_agents: [],
      },
      ...prev,
    ]);
    setDatasetDirty(true);
  };

  const handleSaveDataset = async () => {
    if (!(await ensureCanModify())) return;
    try {
      const res = await fetch("/api/eval/dataset", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Key": getStoredAdminKey(),
        },
        body: JSON.stringify({ items: dataset }),
      });
      if (res.status === 401) {
        markWriteUnauthenticated();
        throw new Error("Admin key required or invalid.");
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      setDatasetDirty(false);
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to save dataset"
      );
    }
  };

  const handleClearDataset = async () => {
    if (!(await ensureCanModify())) return;
    const confirmed = window.confirm(
      "This will clear all evaluation test data from Supabase, not just the UI. Continue?"
    );
    if (!confirmed) return;

    try {
      const res = await fetch("/api/eval/dataset/clear", {
        method: "POST",
        headers: { "X-Admin-Key": getStoredAdminKey() },
      });
      if (res.status === 401) {
        markWriteUnauthenticated();
        throw new Error("Admin key required or invalid.");
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      setDataset([]);
      setDatasetDirty(false);
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to clear dataset"
      );
    }
  };

  const handleDownload = async () => {
    try {
      const res = await fetch("/api/eval/dataset/download");
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "eval_data.jsonl";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to download dataset"
      );
    }
  };

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadFile = async (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const lines = text.split(/\r?\n/);
      const parsed: EvalRow[] = [];
      for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) continue;
        let obj: any;
        try {
          obj = JSON.parse(line);
        } catch (e) {
          throw new Error("Invalid JSONL: could not parse one of the lines.");
        }
        const question = String(obj.question ?? "").trim();
        const groundTruth = String(obj.ground_truth ?? "").trim();
        if (!question || !groundTruth) {
          throw new Error(
            "Each line must include non-empty 'question' and 'ground_truth'."
          );
        }
        const category =
          (obj.category && String(obj.category).trim()) || "general";
        let keywords: string[] = [];
        if (Array.isArray(obj.keywords)) {
          keywords = obj.keywords
            .map((k: any) => String(k).trim())
            .filter(Boolean);
        } else if (typeof obj.keywords === "string") {
          keywords = obj.keywords
            .split(",")
            .map((k: string) => k.trim())
            .filter(Boolean);
        }
        parsed.push({
          question,
          ground_truth: groundTruth,
          category,
          keywords,
        });
      }
      setDataset(parsed);
      setDatasetDirty(true);
      setDatasetError(null);
      setDatasetInfo(
        `Loaded ${parsed.length} rows from JSONL. Click “Save changes” to persist to Supabase.`
      );
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to upload dataset"
      );
      setDatasetInfo(null);
    } finally {
      event.target.value = "";
    }
  };

  const handleGenerateAi = async () => {
    if (!(await ensureCanModify())) return;
    try {
      setGenerating(true);
      setDatasetError(null);
      setDatasetInfo(null);
      const res = await fetch("/api/eval/dataset/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Key": getStoredAdminKey(),
        },
        body: JSON.stringify({ n: clampGenerateN(generateCountInput), mode: "append" }),
      });
      if (res.status === 401) {
        markWriteUnauthenticated();
        throw new Error("Admin key required or invalid.");
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `HTTP ${res.status}`);
      }
      const body = await res.json();
      await loadDataset();
      const gen =
        typeof body.generated_count === "number"
          ? body.generated_count
          : typeof body.count === "number"
            ? body.count
            : null;
      const reqN =
        typeof body.requested_n === "number"
          ? body.requested_n
          : clampGenerateN(generateCountInput);
      if (gen !== null) {
        setDatasetInfo(
          gen < reqN
            ? `AI generated ${gen} of ${reqN} requested test cases (model returned fewer valid rows).`
            : `AI generated ${gen} test cases.`
        );
      } else {
        setDatasetInfo("AI generation completed.");
      }
    } catch (err) {
      setDatasetError(
        err instanceof Error ? err.message : "Failed to generate dataset"
      );
      setDatasetInfo(null);
    } finally {
      setGenerating(false);
    }
  };

  const handleRun = async () => {
    if (!(await ensureCanModify())) return;
    if (pollRef.current) clearTimeout(pollRef.current);
    setJob({ status: "running", started_at: Date.now() / 1000 });
    setJobId(null);
    try {
      const res = await fetch("/api/evaluate", {
        method: "POST",
        headers: { "X-Admin-Key": getStoredAdminKey() },
      });
      if (res.status === 401) {
        markWriteUnauthenticated();
        setJob({
          status: "error",
          error: "Admin key required or invalid.",
        });
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

  const handleRunMultiAgent = async () => {
    if (!(await ensureCanModify())) return;
    if (maPollRef.current) clearTimeout(maPollRef.current);
    setMaJob({ status: "running", started_at: Date.now() / 1000 });
    setMaJobId(null);
    try {
      const res = await fetch("/api/evaluate/multi-agent", {
        method: "POST",
        headers: { "X-Admin-Key": getStoredAdminKey() },
      });
      if (res.status === 401) {
        markWriteUnauthenticated();
        setMaJob({ status: "error", error: "Admin key required or invalid." });
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setMaJobId(data.job_id);
      setMaJob((prev) => ({ ...prev, ...data }));
      maPollRef.current = setTimeout(() => pollMa(data.job_id), 3000);
    } catch (err) {
      setMaJob({
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
          activeTab === "run" ? (
            <button
              type="button"
              onClick={handleRun}
              disabled={isRunning}
              className="flex items-center gap-2 border-2 border-[#000000] bg-[#000000] px-5 py-2.5 font-body text-sm font-bold text-[var(--primary)] hover:bg-[#000000]/80 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {isRunning ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {isRunning ? "Running…" : "Run Evaluation"}
            </button>
          ) : activeTab === "multi_agent" ? (
            <button
              type="button"
              onClick={handleRunMultiAgent}
              disabled={maJob.status === "running"}
              className="flex items-center gap-2 border-2 border-[#000000] bg-[#000000] px-5 py-2.5 font-body text-sm font-bold text-[var(--primary)] hover:bg-[#000000]/80 disabled:opacity-50 transition-colors cursor-pointer"
            >
              {maJob.status === "running" ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4" />}
              {maJob.status === "running" ? "Running…" : "Run Multi-Agent Eval"}
            </button>
          ) : null
        }
      />

      {/* Content */}
      <div className="min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-6 py-8">
        <div className="mx-auto max-w-2xl space-y-6">

          {/* Tabs */}
          <div className="flex gap-2 border-b border-[var(--border)] pb-2 mb-4">
            <button
              type="button"
              onClick={() => setActiveTab("run")}
              className={`px-3 py-1.5 text-xs font-semibold cursor-pointer border-b-2 ${
                activeTab === "run"
                  ? "border-[var(--primary)] text-[var(--foreground)]"
                  : "border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
              }`}
            >
              RAG evaluation
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("multi_agent")}
              className={`px-3 py-1.5 text-xs font-semibold cursor-pointer border-b-2 ${
                activeTab === "multi_agent"
                  ? "border-[var(--primary)] text-[var(--foreground)]"
                  : "border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
              }`}
            >
              Multi-agent eval
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("dataset")}
              className={`px-3 py-1.5 text-xs font-semibold cursor-pointer border-b-2 ${
                activeTab === "dataset"
                  ? "border-[var(--primary)] text-[var(--foreground)]"
                  : "border-transparent text-[var(--foreground-muted)] hover:text-[var(--foreground)]"
              }`}
            >
              Evaluation dataset
            </button>
          </div>

          {activeTab === "run" && (
            <>
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
                    <span className="font-medium">
                      {result?.test_count ?? 0} questions
                    </span>
                    {job.started_at && job.finished_at && (
                      <span className="opacity-70">
                        {" "}
                        in {elapsed(job.started_at, job.finished_at)}
                      </span>
                    )}
                    {!job.started_at && job.finished_at && (
                      <span className="opacity-70">
                        {" "}
                        · last run{" "}
                        {new Date(job.finished_at * 1000).toLocaleString()}
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
                    Click <span className="font-medium">Run Evaluation</span> to
                    start
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
                    {(
                      [
                        "generator_model",
                        "rewrite_model",
                        "reranker_model",
                        "hybrid_search_enabled",
                        "self_check_enabled",
                        "multi_step_enabled",
                      ] as string[]
                    )
                      .filter((k) => result.config_snapshot![k] !== undefined)
                      .map((k) => (
                        <div
                          key={k}
                          className="flex items-center justify-between gap-2"
                        >
                          <span className="text-[var(--foreground-muted)] truncate">
                            {k.replace(/_/g, " ")}
                          </span>
                          <span className="font-mono font-medium text-[var(--foreground)] truncate">
                            {String(result.config_snapshot![k])}
                          </span>
                        </div>
                      ))}
                  </div>
                </SectionCard>
              )}
            </>
          )}

          {activeTab === "multi_agent" && (
            <>
              {maJob.status === "running" && (
                <div className="flex items-center gap-3 border-2 border-[var(--border)] bg-[var(--primary)]/20 px-4 py-3 font-body text-sm font-semibold text-[var(--foreground)]">
                  <RefreshCw className="h-4 w-4 shrink-0 animate-spin text-teal-500" />
                  <span>
                    Running multi-agent evaluation…{" "}
                    {maJob.started_at && <span className="opacity-70">{elapsed(maJob.started_at)} elapsed</span>}
                  </span>
                </div>
              )}
              {maJob.status === "error" && (
                <div className="flex items-center gap-3 rounded-lg border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <span>{maJob.error ?? "Evaluation failed."}</span>
                </div>
              )}
              {maJob.status === "done" && (
                <div className="flex items-center gap-3 border-2 border-[var(--border)] bg-[var(--primary)]/20 px-4 py-3 font-body text-sm font-semibold text-[var(--foreground)]">
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
                  <span>
                    Multi-agent eval complete —{" "}
                    <span className="font-medium">{maJob.result?.total_questions ?? 0} questions</span>
                    {maJob.started_at && maJob.finished_at && (
                      <span className="opacity-70"> in {elapsed(maJob.started_at, maJob.finished_at)}</span>
                    )}
                  </span>
                </div>
              )}
              {maJob.status === "idle" && (
                <div className="rounded-xl border border-dashed border-[var(--border)] px-8 py-16 text-center">
                  <Network className="mx-auto mb-3 h-10 w-10 text-teal-400/50" />
                  <p className="text-sm font-medium text-[var(--foreground-muted)]">No results yet</p>
                  <p className="mt-1 text-xs text-[var(--foreground-muted)]/60">
                    Click <span className="font-medium">Run Multi-Agent Eval</span> to start
                  </p>
                </div>
              )}
              {maJob.result && (
                <>
                  <SectionCard
                    icon={<Network className="h-4 w-4 text-teal-400" />}
                    title="Agent Orchestration"
                  >
                    <div className="space-y-4">
                      <MetricBar
                        label="Agent Routing Accuracy (ARA)"
                        value={maJob.result.agent_routing_accuracy}
                        max={1}
                        format={(v) => `${(v * 100).toFixed(1)}%`}
                      />
                      <MetricBar
                        label="Context Redundancy Ratio (ACRR)"
                        value={maJob.result.agent_context_redundancy_ratio}
                        max={1}
                        format={(v) => v.toFixed(3)}
                      />
                      <MetricBar
                        label="Synthesis Faithfulness"
                        value={maJob.result.synthesis_faithfulness}
                        max={1}
                        format={(v) => v.toFixed(3)}
                      />
                      <MetricBar
                        label="Parallel Efficiency"
                        value={maJob.result.parallel_efficiency}
                        max={1}
                        format={(v) => v.toFixed(3)}
                      />
                    </div>
                  </SectionCard>
                  <SectionCard
                    icon={<Brain className="h-4 w-4 text-violet-400" />}
                    title="Per-Agent MRR"
                  >
                    <div className="space-y-4">
                      {Object.entries(maJob.result.per_agent_mrr).map(([agent, mrr]) => (
                        <MetricBar
                          key={agent}
                          label={agent.replace(/_/g, " ")}
                          value={mrr}
                          max={1}
                          format={(v) => v.toFixed(3)}
                        />
                      ))}
                    </div>
                  </SectionCard>
                </>
              )}
              {maJobId && (
                <p className="text-center text-xs text-[var(--foreground-muted)]/50">
                  Job ID: <code>{maJobId}</code>
                </p>
              )}
            </>
          )}

          {activeTab === "dataset" && (
            <SectionCard
            icon={<Database className="h-4 w-4 text-neutral-300" />}
            title="Evaluation dataset"
            description="Manage the JSONL-backed test questions used by the evaluation suite."
          >
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2 items-center">
                  <button
                    type="button"
                    onClick={handleAddRow}
                    className="border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--background-soft)] cursor-pointer"
                  >
                    Add row
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveDataset}
                    disabled={!datasetDirty || datasetLoading}
                    className="border border-[var(--border)] bg-[var(--primary)] px-3 py-1.5 text-xs font-semibold text-black disabled:opacity-50 cursor-pointer"
                  >
                    Save changes
                  </button>
                  <button
                    type="button"
                    onClick={handleClearDataset}
                    className="border border-red-500/60 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-400 hover:bg-red-500/20 cursor-pointer"
                  >
                    Clear
                  </button>
                  <button
                    type="button"
                    onClick={handleUploadClick}
                    className="border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--background-soft)] cursor-pointer"
                  >
                    Upload JSONL
                  </button>
                  <button
                    type="button"
                    onClick={handleDownload}
                    className="border border-[var(--border)] bg-[var(--background)] px-3 py-1.5 text-xs font-semibold text-[var(--foreground)] hover:bg-[var(--background-soft)] cursor-pointer"
                  >
                    Download JSONL
                  </button>
                  <div className="flex items-center gap-1 text-[10px] text-[var(--foreground-muted)]">
                    <span>AI count:</span>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      aria-label="Number of AI-generated eval rows"
                      value={generateCountInput}
                      onChange={(e) => {
                        const v = e.target.value.replace(/\D/g, "");
                        setGenerateCountInput(v);
                      }}
                      onBlur={normalizeGenerateCountInput}
                      className="w-16 rounded border border-[var(--border)] bg-transparent px-1 py-0.5 text-[10px]"
                    />
                  </div>
                  <button
                    type="button"
                    onClick={handleGenerateAi}
                    disabled={generating}
                    className="border border-[var(--border)] bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50 cursor-pointer"
                  >
                    {generating ? "AI generating…" : "AI generate"}
                  </button>
                </div>
                {(datasetLoading || generating) && (
                  <span className="flex items-center gap-1 text-xs text-[var(--foreground-muted)]">
                    <RefreshCw className="h-3 w-3 animate-spin" />
                    {datasetLoading ? "Loading dataset…" : "Generating test data…"}
                  </span>
                )}
                {!datasetLoading && !generating && (
                  <span className="text-xs text-[var(--foreground-muted)]">
                    {dataset.length} rows
                    {datasetDirty ? " (unsaved)" : ""}
                  </span>
                )}
              </div>

              {datasetError && (
                <p className="text-xs text-red-400">{datasetError}</p>
              )}

              {datasetInfo && (
                <p className="text-xs text-emerald-400">{datasetInfo}</p>
              )}

              <div className="overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--background)]">
                <table className="min-w-full border-collapse text-xs">
                  <thead className="bg-[var(--background-soft)]">
                    <tr>
                      <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold">
                        Question
                      </th>
                      <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold">
                        Ground truth
                      </th>
                      <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold">
                        Keywords
                      </th>
                      <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold">
                        Category
                      </th>
                      <th className="border-b border-[var(--border)] px-3 py-2 text-left font-semibold">
                        Expected agents
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {dataset.map((row, idx) => (
                      <tr key={idx} className="align-top">
                        <td className="border-b border-[var(--border)] px-3 py-2">
                          <textarea
                            className="w-full resize-y rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
                            rows={2}
                            value={row.question}
                            onChange={(e) =>
                              handleCellChange(idx, "question", e.target.value)
                            }
                          />
                        </td>
                        <td className="border-b border-[var(--border)] px-3 py-2">
                          <textarea
                            className="w-full resize-y rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
                            rows={2}
                            value={row.ground_truth}
                            onChange={(e) =>
                              handleCellChange(
                                idx,
                                "ground_truth",
                                e.target.value
                              )
                            }
                          />
                        </td>
                        <td className="border-b border-[var(--border)] px-3 py-2">
                          <input
                            className="w-full rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
                            value={row.keywords.join(", ")}
                            onChange={(e) =>
                              handleCellChange(idx, "keywords", e.target.value)
                            }
                            placeholder="comma,separated,keywords"
                          />
                        </td>
                        <td className="border-b border-[var(--border)] px-3 py-2">
                          <input
                            className="w-full rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
                            value={row.category}
                            onChange={(e) =>
                              handleCellChange(idx, "category", e.target.value)
                            }
                            placeholder="category"
                          />
                        </td>
                        <td className="border-b border-[var(--border)] px-3 py-2">
                          <input
                            className="w-full rounded border border-[var(--border)] bg-transparent px-2 py-1 text-xs"
                            value={(row.expected_agents || []).join(", ")}
                            onChange={(e) =>
                              handleCellChange(idx, "expected_agents", e.target.value)
                            }
                            placeholder="career_agent, skills_agent"
                          />
                        </td>
                      </tr>
                    ))}
                    {dataset.length === 0 && !datasetLoading && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-3 py-6 text-center text-xs text-[var(--foreground-muted)]"
                        >
                          No rows yet. Add a row, upload a JSONL file, or run AI
                          generation.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".jsonl,.txt"
                onChange={handleUploadFile}
                className="hidden"
              />
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
