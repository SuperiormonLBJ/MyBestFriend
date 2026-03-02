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

function TreeFolder({
  node,
  depth,
}: {
  node: FolderNode;
  depth: number;
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
            <TreeDocument key={child.name} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function TreeDocument({
  node,
  depth,
}: {
  node: DocNode;
  depth: number;
}) {
  const [open, setOpen] = useState(false);
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
        <FileText className="h-4 w-4 shrink-0 text-[var(--cta)]" />
        <span className="text-sm text-[var(--foreground)] truncate flex-1">
          {node.name}
        </span>
        <span className="text-xs text-[var(--foreground-muted)] shrink-0">
          {node.chunkCount}
        </span>
      </button>
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
              Ingested documents in the vector store (tree view)
            </p>
          </div>
          <button
            type="button"
            onClick={fetchTree}
            disabled={loading}
            className="flex items-center gap-2 rounded-md border border-[var(--border)] px-3 py-2 text-sm text-[var(--foreground-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto max-w-3xl">
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
                Run the ingestion script from the backend to ingest documents.
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
                  <TreeFolder key={node.name} node={node} depth={0} />
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
