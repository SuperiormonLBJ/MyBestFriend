"use client";

import { useState, useRef, useEffect } from "react";
import { ChatInput } from "@/components/chat-input";
import { ChatMessageBubble, type ChatMessage } from "@/components/chat-message";
import { TypingIndicator } from "@/components/typing-indicator";

async function fetchAnswer(message: string, history: { role: string; content: string }[]) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error("Failed to get response");
  const data = await res.json();
  return data.answer as string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const answer = await fetchAnswer(content, history);

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: answer,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I couldn't connect to the backend. Please make sure the API is running.",
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="shrink-0 border-b border-[var(--border)] px-6 py-4">
        <h2 className="font-heading text-xl font-bold tracking-wider text-[var(--primary)]">
          DIGITAL TWIN
        </h2>
        <p className="mt-1 text-sm text-[var(--foreground-muted)] font-body">
          Ask anything about me — career, projects, hobbies, or daily life
        </p>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <p className="text-[var(--foreground-muted)] font-body">
              Type a question or use the microphone for voice input
            </p>
            <p className="text-sm text-[var(--foreground-muted)]/80 font-body">
              Try: &quot;What is Beiji&apos;s experience at UOB?&quot; or &quot;Tell me about his hobbies&quot;
            </p>
          </div>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
          {loading && <TypingIndicator />}
        </div>
      </div>

      <div className="shrink-0 border-t border-[var(--border)] bg-[var(--background)] p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </div>
    </div>
  );
}
