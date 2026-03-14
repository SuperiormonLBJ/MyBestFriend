"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChevronDown, ChevronUp, FileText } from "lucide-react";
import { Message, MessageContent, MessageAvatar, type MessageRole } from "@/components/ui/message";

export type { MessageRole };

export type SourceItem = {
  source: string;
  section: string;
  doc_type: string;
  year: string;
  snippet: string;
};

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
  sources?: SourceItem[];
};

type ChatMessageProps = {
  message: ChatMessage;
};

const USER_AVATAR_SRC = "/user.png";
const BOT_AVATAR_SRC = "/robot.png";

function SourcesPanel({ sources }: { sources: SourceItem[] }) {
  const [open, setOpen] = useState(false);
  if (!sources.length) return null;

  return (
    <div className="mt-2 border border-[var(--border)] bg-[var(--background)]">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-1.5 font-heading text-[10px] uppercase tracking-widest text-[var(--foreground-muted)] hover:bg-[var(--background-elevated)] transition-colors cursor-pointer"
        aria-expanded={open}
      >
        <FileText className="h-3 w-3 shrink-0" strokeWidth={2.5} />
        <span>{sources.length} source{sources.length > 1 ? "s" : ""}</span>
        {open ? (
          <ChevronUp className="ml-auto h-3 w-3 shrink-0" strokeWidth={2.5} />
        ) : (
          <ChevronDown className="ml-auto h-3 w-3 shrink-0" strokeWidth={2.5} />
        )}
      </button>
      {open && (
        <div className="border-t border-[var(--border)] divide-y divide-[var(--border)]">
          {sources.map((s, i) => (
            <div key={i} className="px-3 py-2 space-y-0.5">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-heading text-[10px] uppercase tracking-wider text-[var(--foreground)] truncate max-w-[200px]">
                  {s.source.replace(/\.md$/, "")}
                </span>
                {s.section && (
                  <span className="font-body text-[10px] text-[var(--foreground-muted)] truncate max-w-[160px]">
                    › {s.section}
                  </span>
                )}
                <div className="ml-auto flex items-center gap-1.5 shrink-0">
                  {s.doc_type && (
                    <span className="rounded-sm border border-[var(--border)] px-1.5 py-0.5 font-heading text-[9px] uppercase tracking-wider text-[var(--foreground-muted)]">
                      {s.doc_type}
                    </span>
                  )}
                  {s.year && (
                    <span className="rounded-sm border border-[var(--border)] px-1.5 py-0.5 font-heading text-[9px] uppercase tracking-wider text-[var(--foreground-muted)]">
                      {s.year}
                    </span>
                  )}
                </div>
              </div>
              {s.snippet && (
                <p className="font-body text-xs text-[var(--foreground-muted)] leading-relaxed line-clamp-2">
                  {s.snippet}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <Message
      from={isUser ? "user" : "assistant"}
      role="article"
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      <div className={`flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <span className="font-heading text-[11px] uppercase tracking-[0.18em] text-[var(--foreground-muted)] px-0.5">
          {isUser ? "YOU" : "BOT"}
        </span>
        <MessageContent>
          {isUser ? (
            <p className="whitespace-pre-wrap text-base leading-snug font-body font-semibold">{message.content}</p>
          ) : (
            <div className="prose max-w-none font-body text-[var(--foreground)] prose-headings:font-heading prose-headings:text-[var(--foreground)] prose-strong:text-[var(--foreground)] prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-p:my-2 prose-p:leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </MessageContent>
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full max-w-full">
            <SourcesPanel sources={message.sources} />
          </div>
        )}
      </div>
      <MessageAvatar
        src={isUser ? USER_AVATAR_SRC : BOT_AVATAR_SRC}
        name={isUser ? "User" : "AI"}
        className={isUser ? "ring-[#0d9488] [box-shadow:2px_2px_0_0_#0d9488]" : "ring-border [box-shadow:2px_2px_0_0_var(--border)]"}
      />
    </Message>
  );
}
