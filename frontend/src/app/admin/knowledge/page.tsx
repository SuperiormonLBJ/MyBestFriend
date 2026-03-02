"use client";

import { useState, useEffect } from "react";
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

const DOC_TYPES = ["projects", "career", "cv", "personal", "misc"];

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
  const [addForm, setAddForm] = useState({ filename: "", doc_type: "projects", content: "" });

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

  const handleDelete = async (source: string, docType: string) => {
    if (!confirm(`Delete "${source}" and all its chunks? This cannot be undone.`)) return;
    setDeleting(source);
    setMessage(null);
    try {
      const res = await fetch(
        `/api/documents/${encodeURIComponent(source)}?doc_type=${encodeURIComponent(docType)}`,
        { method: "DELETE" }
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
  };

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addForm.filename.trim() || !addForm.content.trim()) return;
    setAdding(true);
    setMessage(null);
    try {
      const res = await fetch("/api/documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
      setAddForm({ filename: "", doc_type: "projects", content: "" });
      setShowAdd(false);
      await fetchTree();
    } catch (err) {
      setMessage({ type: "error", text: err instanceof Error ? err.message : "Add failed" });
    } finally {
      setAdding(false);
    }
  };

  const handleReingest = async () => {
    if (
      !confirm(
        "Re-ingest all documents from the data folder? This will replace the current vector store. Continue?"
      )
    )
      return;
    setIngesting(true);
    setMessage(null);
    try {
      const res = await fetch("/api/ingest", { method: "POST" });
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
  };

  return (
    <div className="flex min-h-full flex-1 flex-col">
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <Link
              href="/admin"
              className="text-sm text-[var(--foreground-muted)] hover:text-[var(--primary)] mb-2 inline-block"
            >
              ← Admin Panel
            </Link>
            <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
              KNOWLEDGE BASE
            </h2>
            <p className="mt-1 text-sm text-[var(--foreground-muted)] font-body">
              View, add, and delete documents in the vector store
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-2 rounded-md bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--background)] hover:bg-[var(--primary-hover)] transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add document
            </button>
            <button
              type="button"
              onClick={handleReingest}
              disabled={ingesting}
              className="flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors disabled:opacity-50"
              title="Re-ingest all documents from the data folder"
            >
              <RotateCw className={`h-4 w-4 ${ingesting ? "animate-spin" : ""}`} />
              {ingesting ? "Re-ingesting…" : "Re-ingest all"}
            </button>
            <button
              type="button"
              onClick={fetchTree}
              disabled={loading}
              className="flex items-center gap-2 rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors disabled:opacity-50"
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
              className={`flex items-center gap-2 rounded-lg border px-4 py-3 ${
                message.type === "success"
                  ? "border-[var(--primary)]/50 bg-[var(--primary)]/10 text-[var(--primary)]"
                  : "border-red-500/50 bg-red-500/10 text-red-400"
              }`}
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{message.text}</span>
            </div>
          )}

          {showAdd && (
            <form
              onSubmit={handleAdd}
              className="rounded-lg border border-[var(--border)] bg-[var(--background-elevated)] p-6"
            >
              <h3 className="mb-4 font-semibold text-[var(--foreground)]">Add new document</h3>
              <div className="space-y-4">
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
                    Markdown content
                  </label>
                  <textarea
                    value={addForm.content}
                    onChange={(e) => setAddForm((p) => ({ ...p, content: e.target.value }))}
                    placeholder="# Title&#10;&#10;Your content here..."
                    rows={10}
                    className="w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-[var(--foreground)] placeholder:text-[var(--foreground-muted)]/60 font-mono text-sm"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={adding || !addForm.filename.trim() || !addForm.content.trim()}
                    className="rounded-md bg-[var(--primary)] px-4 py-2 text-sm font-medium text-[var(--background)] hover:bg-[var(--primary-hover)] disabled:opacity-50"
                  >
                    {adding ? "Adding…" : "Add document"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowAdd(false)}
                    className="rounded-md border border-[var(--border)] px-4 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </form>
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
