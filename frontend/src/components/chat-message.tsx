"use client";

import { User, Bot } from "lucide-react";

export type MessageRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: MessageRole;
  content: string;
};

type ChatMessageProps = {
  message: ChatMessage;
};

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
      role="article"
      aria-label={isUser ? "Your message" : "Assistant message"}
    >
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${
          isUser ? "bg-[var(--primary)] text-[#08090C]" : "bg-[var(--chat-assistant-bg)] text-[var(--primary)] border border-[var(--border)]"
        }`}
      >
        {isUser ? (
          <User className="h-4 w-4" strokeWidth={2} />
        ) : (
          <Bot className="h-4 w-4" strokeWidth={2} />
        )}
      </div>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 border ${
          isUser
            ? "bg-[var(--chat-user-bg)] text-[#08090C] border-[var(--primary)]/50 shadow-[0_0_8px_var(--primary-glow)]"
            : "bg-[var(--chat-assistant-bg)] text-[var(--foreground)] border-[var(--border)]"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
      </div>
    </div>
  );
}
