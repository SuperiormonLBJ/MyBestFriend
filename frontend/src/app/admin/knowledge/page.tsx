"use client";

import { useState, useEffect, useRef } from "react";
import { getStoredAdminKey } from "@/lib/session-auth";
import Link from "next/link";
import {
  ChevronRight,
  ChevronDown,
  Folder,
  FileText,
  Database,
  RefreshCw,
  AlertCircle,
  Plus,
  Trash2,
  RotateCw,
  Sparkles,
  Eye,
  ArrowLeft,
  BrainCircuit,
  Loader2,
  Zap,
  TriangleAlert,
  X,
} from "lucide-react";

type ChunkInfo = { preview: string; section: string };

type DocNode = {
  name: string;
  type: "document";
  chunkCount: number;
  chunks: ChunkInfo[];
};

type FolderNode = {
  name: string;
  type: "folder";
  chunkCount: number;
  children: DocNode[];
};

type TreeData = {
  tree: FolderNode[];
  totalChunks: number;
  error?: string;
};

const DOC_TYPES = ["project", "career", "cv", "personal", "misc"];

const PHASE_MESSAGES: Record<string, string[]> = {
  restructure: [
    "Analyzing raw text…",
    "Mapping document structure…",
    "Generating frontmatter…",
    "Structuring sections…",
    "Applying RAG signals…",
    "Polishing markdown…",
  ],
  ingest: [
    "Parsing markdown…",
    "Splitting into chunks…",
    "Computing embeddings…",
    "Writing to vector store…",
    "Indexing metadata…",
  ],
  reingest: [
    "Loading all documents…",
    "Rebuilding chunk tree…",
    "Generating embeddings…",
    "Replacing vector store…",
    "Finalizing index…",
  ],
};

function useSimulatedProgress(active: boolean) {
  const [pct, setPct] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef(0);

  useEffect(() => {
    if (!active) {
      if (pct > 0) {
        setPct(100);
        const t = setTimeout(() => setPct(0), 500);
        return () => clearTimeout(t);
      }
      return;
    }
    startRef.current = Date.now();
    setPct(0);
    const tick = () => {
      const elapsed = (Date.now() - startRef.current) / 1000;
      // Fast at first, asymptotically approaches 92%
      const next = 92 * (1 - Math.exp(-elapsed / 12));
      setPct(Math.min(next, 92));
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [active]);

  return pct;
}

function ProcessingOverlay({
  phase,
}: {
  phase: "restructure" | "ingest" | "reingest";
}) {
  const [msgIdx, setMsgIdx] = useState(0);
  const messages = PHASE_MESSAGES[phase];

  useEffect(() => {
    setMsgIdx(0);
    const iv = setInterval(() => {
      setMsgIdx((i) => (i + 1) % messages.length);
    }, 2800);
    return () => clearInterval(iv);
  }, [phase, messages.length]);

  const Icon = phase === "restructure" ? BrainCircuit : phase === "ingest" ? Zap : Loader2;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--background)]/80 backdrop-blur-sm">
      {/* Scanline effect */}
      <div
        className="pointer-events-none absolute inset-0 overflow-hidden opacity-[0.04]"
        aria-hidden
      >
        <div
          className="absolute left-0 w-full h-16 bg-gradient-to-b from-transparent via-[var(--primary)] to-transparent"
          style={{ animation: "scanline 3s linear infinite" }}
        />
      </div>

      <div className="relative w-full max-w-sm mx-4 rounded-xl border border-[var(--border)] bg-[var(--background-elevated)] p-8 text-center space-y-6">
        <div className="flex justify-center">
          <div className="relative">
            <Icon
              className={`h-12 w-12 text-[var(--primary)] ${
                phase === "restructure" ? "animate-pulse" : "animate-spin"
              }`}
              style={{ animationDuration: phase === "restructure" ? "1.5s" : "2s" }}
            />
            <div className="absolute inset-0 rounded-full blur-xl bg-[var(--primary)] opacity-20 animate-pulse" />
          </div>
        </div>

        <div>
          <h4 className="font-heading text-lg uppercase tracking-wide text-[var(--foreground)] mb-1">
            {phase === "restructure"
              ? "RESTRUCTURING"
              : phase === "ingest"
                ? "INGESTING"
                : "RE-INGESTING ALL"}
          </h4>
          <p className="text-sm text-[var(--foreground-muted)] h-5 transition-opacity duration-300">
            {messages[msgIdx]}
          </p>
        </div>

        <div className="progress-bar-track">
          <div className="progress-bar-fill" id="overlay-progress" />
        </div>

        <p className="text-xs text-[var(--foreground-muted)]/60 font-body">
          Please wait — do not navigate away
        </p>
      </div>
    </div>
  );
}

function ConfirmModal({
  open,
  title,
  message,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--background)]/80 backdrop-blur-sm">
      <div className="relative w-full max-w-md mx-4 rounded-xl border border-red-500/40 bg-[var(--background-elevated)] p-6 space-y-5 shadow-lg shadow-red-500/10">
        <button
          type="button"
          onClick={onCancel}
          className="absolute top-4 right-4 text-[var(--foreground-muted)] hover:text-[var(--foreground)] transition-colors"
        >
          <X className="h-4 w-4" />
        </button>

        <div className="flex items-start gap-4">
          <div className="shrink-0 flex items-center justify-center w-10 h-10 rounded-full bg-red-500/15">
            <TriangleAlert className="h-5 w-5 text-red-400" />
          </div>
          <div>
            <h4 className="font-heading text-base font-bold tracking-wider text-[var(--foreground)]">
              {title}
            </h4>
            <p className="mt-1 text-sm text-[var(--foreground-muted)] leading-relaxed">
              {message}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-3 pt-1">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="rounded-md bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 transition-colors"
          >
            {confirmLabel ?? "Confirm"}
          </button>
        </div>
      </div>
    </div>
  );
}

function TreeFolder({
  node,
  depth,
  onDelete,
  deleting,
}: {
  node: FolderNode;
  depth: number;
  onDelete: (source: string, docType: string) => void;
  deleting: string | null;
}) {
  const [open, setOpen] = useState(depth < 2);
  return (
    <div className="select-none">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left hover:bg-[var(--primary)]/10 transition-colors"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {open ? (
          <ChevronDown className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" />
        ) : (
          <ChevronRight className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" />
        )}
        <Folder className="h-4 w-4 shrink-0 text-[var(--primary)]" />
        <span className="font-medium text-[var(--foreground)] truncate">
          {node.name}
        </span>
        <span className="ml-auto text-xs text-[var(--foreground-muted)] shrink-0">
          {node.chunkCount} chunks
        </span>
      </button>
      {open && (
        <div className="border-l border-[var(--border)] ml-4 mt-1">
          {node.children.map((child) => (
            <TreeDocument
              key={child.name}
              node={child}
              depth={depth + 1}
              docType={node.name}
              onDelete={onDelete}
              deleting={deleting}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function TreeDocument({
  node,
  depth,
  docType,
  onDelete,
  deleting,
}: {
  node: DocNode;
  depth: number;
  docType: string;
  onDelete: (source: string, docType: string) => void;
  deleting: string | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="select-none">
      <div
        className="flex items-center gap-2 rounded px-2 py-1.5 hover:bg-[var(--primary)]/10 transition-colors group"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="flex flex-1 items-center gap-2 text-left min-w-0"
        >
          {open ? (
            <ChevronDown className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" />
          ) : (
            <ChevronRight className="h-4 w-4 shrink-0 text-[var(--foreground-muted)]" />
          )}
          <FileText className="h-4 w-4 shrink-0 text-[var(--cta)]" />
          <span className="text-sm text-[var(--foreground)] truncate flex-1">
            {node.name}
          </span>
          <span className="text-xs text-[var(--foreground-muted)] shrink-0">
            {node.chunkCount}
          </span>
        </button>
        <button
          type="button"
          onClick={() => onDelete(node.name, docType)}
          disabled={deleting === node.name}
          className="rounded p-1.5 text-red-400 hover:bg-red-500/20 disabled:opacity-50 opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
          title="Delete document"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      {open && (
        <div
          className="border-l border-[var(--border)] ml-4 mt-1 space-y-2"
          style={{ paddingLeft: `${depth * 8 + 8}px` }}
        >
          {node.chunks.map((chunk, i) => (
            <div
              key={i}
              className="rounded-md border border-[var(--border)] bg-[var(--background)] p-3 text-sm"
            >
              {chunk.section && (
                <div className="text-xs font-medium text-[var(--primary)] mb-1">
                  {chunk.section}
                </div>
              )}
              <p className="text-[var(--foreground-muted)] line-clamp-3">
                {chunk.preview}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function KnowledgePage() {
  const [data, setData] = useState<TreeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [restructureLoading, setRestructureLoading] = useState(false);
  type AddStep = "input" | "review";
  const [addStep, setAddStep] = useState<AddStep>("input");
  const [addForm, setAddForm] = useState({
    rawText: "",
    doc_type: "career",
    year: "",
    importance: "medium",
    filename: "",
    content: "",
  });
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    onConfirm: () => void;
  } | null>(null);

  const busyPhase = restructureLoading
    ? "restructure"
    : adding
      ? "ingest"
      : ingesting
        ? "reingest"
        : null;
  const isBusy = busyPhase !== null;
  const progressPct = useSimulatedProgress(isBusy);

  // Drive the CSS width of the overlay progress bar
  useEffect(() => {
    const el = document.getElementById("overlay-progress");
    if (el) el.style.width = `${progressPct}%`;
  }, [progressPct]);

  const fetchTree = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/knowledge");
      const json = await res.json();
      setData(json);
    } catch {
      setData({ tree: [], totalChunks: 0, error: "Failed to load" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTree();
  }, []);

  const handleDelete = (source: string, docType: string) => {
    setConfirmDialog({
      title: "Delete document",
      message: `Delete "${source}" and all its chunks? This cannot be undone.`,
      confirmLabel: "Delete",
      onConfirm: async () => {
        setConfirmDialog(null);
        setDeleting(source);
        setMessage(null);
        try {
          const res = await fetch(
            `/api/documents/${encodeURIComponent(source)}?doc_type=${encodeURIComponent(docType)}`,
            { method: "DELETE", headers: { "X-Admin-Key": getStoredAdminKey() } }
          );
          const resData = await res.json();
          if (resData.error) throw new Error(resData.error);
          setMessage({ type: "success", text: `Deleted ${source} (${resData.deleted_chunks ?? 0} chunks)` });
          await fetchTree();
        } catch (err) {
          setMessage({ type: "error", text: err instanceof Error ? err.message : "Delete failed" });
        } finally {
          setDeleting(null);
        }
      },
    });
  };

  const handleRestructure = async () => {
    if (!addForm.rawText.trim()) return;
    setRestructureLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/restructure", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Key": getStoredAdminKey() },
        body: JSON.stringify({
          raw_text: addForm.rawText.trim(),
          doc_type: addForm.doc_type,
          year: addForm.year.trim() || undefined,
          importance: addForm.importance,
        }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.error || resData.detail || "Restructure failed");
      if (resData.error) throw new Error(resData.error);
      setAddForm((p) => ({ ...p, content: resData.restructured_md ?? "" }));
      setAddStep("review");
      setMessage({ type: "success", text: "Restructured. Review the markdown below and edit if needed, then confirm to ingest." });
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "Restructure failed" });
    } finally {
      setRestructureLoading(false);
    }
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm.filename.trim() || !addForm.content.trim()) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch("/api/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Key": getStoredAdminKey() },
        body: JSON.stringify({
          filename: addForm.filename,
          doc_type: addForm.doc_type,
          content: addForm.content,
        }),
      });
      const resData = await res.json();
      if (!res.ok) throw new Error(resData.detail || resData.error || `HTTP ${res.status}`);
      if (resData.error) throw new Error(resData.error);
      setMessage({ type: "success", text: `Added ${addForm.filename} (${resData.chunks_added ?? 0} chunks)` });
      setAddForm({ rawText: "", doc_type: "career", year: "", importance: "medium", filename: "", content: "" });
      setAddStep("input");
      setShowAdd(false);
      await fetchTree();
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "Add failed" });
    } finally {
      setAdding(false);
    }
  };

  const handleReingest = () => {
    setConfirmDialog({
      title: "Re-ingest all documents",
      message: "This will replace the current vector store with freshly ingested documents from the data folder. Continue?",
      confirmLabel: "Re-ingest",
      onConfirm: async () => {
        setConfirmDialog(null);
        setIngesting(true);
        setMessage(null);
        try {
          const res = await fetch("/api/ingest", { method: "POST", headers: { "X-Admin-Key": getStoredAdminKey() } });
          const resData = await res.json();
          if (!res.ok) throw new Error(resData.error || resData.detail || `HTTP ${res.status}`);
          setMessage({
            type: "success",
            text: `Re-ingestion complete. ${resData.chunks_count ?? 0} chunks in vector store.`,
          });
          await fetchTree();
        } catch (err) {
          setMessage({
            type: "error",
            text: err instanceof Error ? err.message : "Re-ingestion failed",
          });
        } finally {
          setIngesting(false);
        }
      },
    });
  };

  return (
    <div className="flex min-h-full flex-1 flex-col">
      {busyPhase && <ProcessingOverlay phase={busyPhase} />}
      <ConfirmModal
        open={confirmDialog !== null}
        title={confirmDialog?.title ?? ""}
        message={confirmDialog?.message ?? ""}
        confirmLabel={confirmDialog?.confirmLabel}
        onConfirm={() => confirmDialog?.onConfirm()}
        onCancel={() => setConfirmDialog(null)}
      />
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture">
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/admin"
              className="mb-2 inline-block font-body text-sm font-semibold text-[#000000]/60 hover:text-[#000000]"
            >
              ← Admin Panel
            </Link>
            <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide">
              KNOWLEDGE BASE
            </h2>
            <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest">
              View, add, and delete documents in the vector store
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-2 border-2 border-[#000000] bg-[#000000] px-4 py-2 font-body text-sm font-bold text-[var(--primary)] hover:bg-[#000000]/80 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add document
            </button>
            <button
              type="button"
              onClick={handleReingest}
              disabled={ingesting}
              className="flex items-center gap-2 border-2 border-[#000000]/50 px-4 py-2 font-body text-sm font-bold text-[#000000]/80 hover:border-[#000000] hover:bg-[#000000]/10 transition-colors disabled:opacity-50"
              title="Re-ingest all documents from the data folder"
            >
              <RotateCw className={`h-4 w-4 ${ingesting ? "animate-spin" : ""}`} />
              {ingesting ? "Re-ingesting…" : "Re-ingest all"}
            </button>
            <button
              type="button"
              onClick={fetchTree}
              disabled={loading}
              className="flex items-center gap-2 border-2 border-[#000000]/50 px-4 py-2 font-body text-sm font-bold text-[#000000]/80 hover:border-[#000000] hover:bg-[#000000]/10 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-3xl space-y-6">
          {message && (
            <div
              className={`flex items-center gap-2 border-2 px-4 py-3 font-body text-sm font-semibold ${
                message.type === "success"
                  ? "border-[var(--border)] bg-[var(--primary)]/20 text-[var(--foreground)]"
                  : "border-red-500 bg-red-500/10 text-red-500"
              }`}
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{message.text}</span>
            </div>
          )}

          {showAdd && (
            <div className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6">
              <h3 className="mb-4 font-semibold text-[var(--foreground)]">
                {addStep === "input" ? "Add new document (raw text → AI structure → review)" : "Review & ingest"}
              </h3>

              {addStep === "input" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                        Type
                      </label>
                      <select
                        value={addForm.doc_type}
                        onChange={(e) => setAddForm((p) => ({ ...p, doc_type: e.target.value }))}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)]"
                      >
                        {DOC_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                        Year
                      </label>
                      <input
                        type="text"
                        value={addForm.year}
                        onChange={(e) => setAddForm((p) => ({ ...p, year: e.target.value }))}
                        placeholder="e.g. 2023"
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/60"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                        Importance
                      </label>
                      <select
                        value={addForm.importance}
                        onChange={(e) => setAddForm((p) => ({ ...p, importance: e.target.value }))}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)]"
                      >
                        <option value="high">high</option>
                        <option value="medium">medium</option>
                        <option value="low">low</option>
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                      Raw text (resume, notes, LinkedIn paste, etc.)
                    </label>
                    <textarea
                      value={addForm.rawText}
                      onChange={(e) => setAddForm((p) => ({ ...p, rawText: e.target.value }))}
                      placeholder="Paste any unstructured text here. The AI will restructure it into RAG-ready markdown (like career/project format)."
                      rows={12}
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/60 font-mono text-sm"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={handleRestructure}
                      disabled={restructureLoading || !addForm.rawText.trim()}
                      className="flex items-center gap-2 border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-2 font-body text-sm font-bold text-[#000000] hover:bg-[var(--primary-hover)] disabled:opacity-50"
                    >
                      <Sparkles className={`h-4 w-4 ${restructureLoading ? "animate-pulse" : ""}`} />
                      {restructureLoading ? "Restructuring…" : "Restructure with AI"}
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowAdd(false); setAddStep("input"); setAddForm({ rawText: "", doc_type: "career", year: "", importance: "medium", filename: "", content: "" }); }}
                      className="rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {addStep === "review" && (
                <form onSubmit={handleAdd} className="space-y-4">
                  <p className="text-sm text-[var(--foreground-muted)] flex items-center gap-2">
                    <Eye className="h-4 w-4" />
                    Edit the markdown below if needed, then set filename and confirm to ingest.
                  </p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                        Filename (.md)
                      </label>
                      <input
                        type="text"
                        value={addForm.filename}
                        onChange={(e) => setAddForm((p) => ({ ...p, filename: e.target.value }))}
                        placeholder="my-doc.md"
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/60"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                        Category
                      </label>
                      <select
                        value={addForm.doc_type}
                        onChange={(e) => setAddForm((p) => ({ ...p, doc_type: e.target.value }))}
                        className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)]"
                      >
                        {DOC_TYPES.map((t) => (
                          <option key={t} value={t}>{t}</option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-[var(--foreground-muted)] mb-1">
                      Markdown (editable before ingest)
                    </label>
                    <textarea
                      value={addForm.content}
                      onChange={(e) => setAddForm((p) => ({ ...p, content: e.target.value }))}
                      rows={14}
                      className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] font-mono text-sm"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="submit"
                      disabled={adding || !addForm.filename.trim() || !addForm.content.trim()}
                      className="border-2 border-[var(--border)] bg-[var(--cta)] px-4 py-2 font-body text-sm font-bold text-white hover:opacity-90 disabled:opacity-50"
                    >
                      {adding ? "Ingesting…" : "Confirm & Ingest"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setAddStep("input")}
                      className="flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      Back to edit raw text
                    </button>
                    <button
                      type="button"
                      onClick={() => { setShowAdd(false); setAddStep("input"); setAddForm({ rawText: "", doc_type: "career", year: "", importance: "medium", filename: "", content: "" }); }}
                      className="rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          <div>
            <h3 className="mb-4 font-semibold text-[var(--foreground)]">Documents</h3>
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <Database className="h-12 w-12 animate-pulse text-[var(--primary)]/50" />
              </div>
            ) : data?.error ? (
              <div className="flex items-center gap-2 rounded-lg border border-red-500/50 bg-red-500/10 px-4 py-3 text-red-400">
                <AlertCircle className="h-5 w-5 shrink-0" />
                <span>{data.error}</span>
              </div>
            ) : !data?.tree?.length ? (
              <div className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-8 text-center text-[var(--foreground-muted)]">
                <Database className="mx-auto h-12 w-12 text-[var(--primary)]/30 mb-4" />
                <p>No documents ingested yet.</p>
                <p className="mt-2 text-sm">
                  Add a document above or run the ingestion script from the backend.
                </p>
              </div>
            ) : (
              <>
                <div className="mb-4 flex items-center gap-2 text-sm text-[var(--foreground-muted)]">
                  <Database className="h-4 w-4" />
                  <span>
                    {data.totalChunks} total chunks across {data.tree.length} categories
                  </span>
                </div>
                <div className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-4">
                  {data.tree.map((node) => (
                    <TreeFolder
                      key={node.name}
                      node={node}
                      depth={0}
                      onDelete={handleDelete}
                      deleting={deleting}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
