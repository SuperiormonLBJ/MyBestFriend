"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export type MessageRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
};

type ChatMessageProps = {
  message: ChatMessage;
};

function UserAvatar() {
  return (
    <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="16" cy="11" r="5" fill="currentColor" stroke="currentColor" strokeWidth="2"/>
      <path d="M6 28c0-5.523 4.477-10 10-10s10 4.477 10 10" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square"/>
    </svg>
  );
}

function BotAvatar() {
  return (
    <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="6" y="10" width="20" height="16" fill="currentColor" stroke="currentColor" strokeWidth="2"/>
      <rect x="10" y="14" width="4" height="4" fill="var(--background)" stroke="var(--background)" strokeWidth="0.5"/>
      <rect x="18" y="14" width="4" height="4" fill="var(--background)" stroke="var(--background)" strokeWidth="0.5"/>
      <path d="M12 22h8" stroke="var(--background)" strokeWidth="2" strokeLinecap="square"/>
      <path d="M16 10V6" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
      <circle cx="16" cy="5" r="1.5" fill="currentColor"/>
    </svg>
  );
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
      role="article"
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      <div
        className={`flex h-9 w-9 shrink-0 items-center justify-center border-[3px] border-[var(--border)] ${
          isUser
            ? "bg-[var(--primary)] text-[#000000]"
            : "bg-[var(--background-elevated)] text-[var(--foreground)]"
        }`}
        style={{ boxShadow: "2px 2px 0 var(--border)" }}
      >
        {isUser ? <UserAvatar /> : <BotAvatar />}
      </div>
      <div className={`flex max-w-[80%] flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
        <span className="font-heading text-[11px] uppercase tracking-[0.18em] text-[var(--foreground-muted)] px-0.5">
          {isUser ? "YOU" : "BOT"}
        </span>
        <div
          className={`px-4 py-3 border-[3px] border-[var(--border)] ${
            isUser
              ? "bg-[var(--chat-user-bg)] text-[#000000]"
              : "bg-[var(--chat-assistant-bg)] text-[var(--foreground)]"
          }`}
          style={{ boxShadow: "4px 4px 0 var(--border)" }}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-base leading-snug font-body font-semibold">{message.content}</p>
          ) : (
            <div className="prose max-w-none font-body text-[var(--foreground)] prose-headings:font-heading prose-headings:text-[var(--foreground)] prose-strong:text-[var(--foreground)] prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5 prose-p:my-2 prose-p:leading-relaxed">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
