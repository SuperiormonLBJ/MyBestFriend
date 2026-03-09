"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { SquarePen } from "lucide-react";
import { ChatInput } from "@/components/chat-input";
import { ChatMessageBubble, type ChatMessage, type SourceItem } from "@/components/chat-message";
import { TypingIndicator } from "@/components/typing-indicator";
import { useConfig } from "@/components/config-provider";

const HISTORY_KEY = "chat_history";

type ContactState = "idle" | "open" | "sending" | "sent" | "error";

type KnowledgeScope = {
  doc_types: Record<string, number>;
  year_range: string | null;
};

const QUICK_PROMPTS = [
  "What is {name}'s current role?",
  "Tell me about {name}'s projects",
  "What skills does {name} have?",
  "What are {name}'s hobbies?",
  "Summarize {name}'s career",
  "What did {name} study?",
];

export default function ChatPage() {
  const { config } = useConfig();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [scope, setScope] = useState<KnowledgeScope | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const [pendingQuestion, setPendingQuestion] = useState("");
  const [contactState, setContactState] = useState<ContactState>("idle");
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [contactError, setContactError] = useState("");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(HISTORY_KEY);
      if (saved) setMessages(JSON.parse(saved));
    } catch {}
    setHistoryLoaded(true);
  }, []);

  useEffect(() => {
    if (!historyLoaded) return;
    try {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(messages));
    } catch {}
  }, [messages, historyLoaded]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading, contactState]);

  // Fetch knowledge scope for onboarding display
  useEffect(() => {
    fetch("/api/scope")
      .then((r) => r.json())
      .then((d) => setScope(d))
      .catch(() => {});
  }, []);

  const handleSend = useCallback(async (content: string) => {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
    };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setContactState("idle");
    setPendingQuestion("");

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content, history }),
      });

      if (!res.ok) throw new Error("Failed to get response");

      const assistantId = crypto.randomUUID();
      let accumulated = "";
      let firstToken = true;
      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      const processEvent = (event: Record<string, unknown>, isFinal: boolean) => {
        if (event.done) {
          const text = ((event.final as string) ?? accumulated).trim() || "No response generated.";
          const sources = (event.sources as SourceItem[]) || [];
          if (firstToken) {
            setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: text, sources }]);
            firstToken = false;
          } else {
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: text, sources } : m))
            );
          }
          setStreaming(false);
          if (event.no_info) {
            setPendingQuestion(content);
            setContactState("open");
          }
        } else if (event.token) {
          const token = event.token as string;
          if (firstToken) {
            firstToken = false;
            accumulated = token;
            setMessages((prev) => [...prev, { id: assistantId, role: "assistant", content: accumulated }]);
            setLoading(false);
            setStreaming(true);
          } else {
            accumulated += token;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: accumulated } : m))
            );
          }
        }
      };

      while (true) {
        const { done: readerDone, value } = await reader.read();
        if (readerDone) {
          if (value) buffer += decoder.decode(value, { stream: false });
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          try {
            processEvent(JSON.parse(part.slice(6)), false);
          } catch (e) {
            console.error("[chat] SSE parse error:", part.slice(0, 80), e);
          }
        }
      }

      const flushParts = buffer.trim() ? buffer.trim().split("\n\n") : [];
      for (const part of flushParts) {
        if (!part.startsWith("data: ")) continue;
        try {
          processEvent(JSON.parse(part.slice(6)), true);
        } catch (e) {
          console.error("[chat] SSE parse error (flush):", part.slice(0, 80), e);
        }
      }

      if (firstToken) {
        setMessages((prev) => [
          ...prev,
          {
            id: assistantId,
            role: "assistant",
            content:
              "No response was received from the server. The request may have timed out (try a shorter question) or the stream may not have reached the browser.",
          },
        ]);
        setStreaming(false);
      }
    } catch (err) {
      console.error("[chat] stream error:", err);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Sorry, I couldn't connect to the backend. Please make sure the API is running.",
        },
      ]);
      setStreaming(false);
    } finally {
      setLoading(false);
    }
  }, [messages]);

  const handleContactSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contactName.trim() || !contactEmail.trim()) {
      setContactError("Please fill in both your name and email.");
      return;
    }
    setContactError("");
    setContactState("sending");
    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester_name: contactName.trim(),
          requester_email: contactEmail.trim(),
          question: pendingQuestion,
        }),
      });
      if (!res.ok) throw new Error("send failed");
      setContactState("sent");
      setContactName("");
      setContactEmail("");
    } catch {
      setContactState("error");
    }
  };

  const handleNewChat = () => {
    try { localStorage.removeItem(HISTORY_KEY); } catch {}
    setMessages([]);
    setContactState("idle");
    setPendingQuestion("");
    setContactName("");
    setContactEmail("");
    setContactError("");
  };

  const ownerName = config.owner_name || "Beiji";

  // Quick prompts with owner name substituted
  const quickPrompts = QUICK_PROMPTS.slice(0, 4).map((p) => p.replace("{name}", ownerName));

  // Knowledge scope summary for onboarding
  const docTypeLabels: Record<string, string> = {
    career: "Career & Work",
    project: "Projects",
    personal: "Personal & Hobbies",
    cv: "CV & Skills",
    misc: "General",
  };
  const scopeTopics = scope
    ? Object.keys(scope.doc_types)
        .filter((t) => scope.doc_types[t] > 0)
        .map((t) => docTypeLabels[t] || t)
    : null;

  return (
    <div className="flex h-full flex-1 flex-col">
      <header className="shrink-0 border-b-2 border-[var(--border)] bg-[var(--primary)] px-6 py-4 header-texture flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl text-[#000000] uppercase tracking-wide glitch-title">
            DIGITAL TWIN
          </h2>
          <p className="mt-1 font-body text-base font-bold text-[#000000]/75 uppercase tracking-widest blinking-cursor">
            Ask anything about <span className="underline">{ownerName}</span> — career, projects, hobbies, or daily life
          </p>
        </div>
        <button
          type="button"
          onClick={handleNewChat}
          aria-label="New chat"
          title="New chat"
          className="flex shrink-0 items-center gap-2 border-2 border-[#000000] px-3 py-2 font-heading text-sm uppercase tracking-wide text-[#000000] transition-colors duration-150 hover:bg-[#000000] hover:text-[var(--primary)] cursor-pointer"
          style={{ boxShadow: "3px 3px 0 rgba(0,0,0,0.35)" }}
        >
          <SquarePen className="h-4 w-4 shrink-0" strokeWidth={2.5} />
          New Chat
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4"
        role="log"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
            <div className="border-2 border-[var(--border)] px-8 py-6 w-full max-w-lg" style={{ boxShadow: "5px 5px 0 var(--border)" }}>
              <p className="font-body text-base font-semibold text-[var(--foreground-muted)] uppercase tracking-wide">
                Ask me anything about {ownerName}
              </p>
              {scopeTopics && scopeTopics.length > 0 && (
                <div className="mt-3 flex flex-wrap justify-center gap-2">
                  {scopeTopics.map((topic) => (
                    <span
                      key={topic}
                      className="border border-[var(--border)] px-2.5 py-1 font-body text-xs text-[var(--foreground-muted)] uppercase tracking-wider"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              )}
              {scope?.year_range && (
                <p className="mt-2 font-body text-xs text-[var(--foreground-muted)]/60">
                  Knowledge covers {scope.year_range}
                </p>
              )}
            </div>

            {/* Quick prompt chips */}
            <div className="w-full max-w-lg space-y-2">
              <p className="font-heading text-[10px] uppercase tracking-widest text-[var(--foreground-muted)]">
                Try asking
              </p>
              <div className="grid grid-cols-2 gap-2">
                {quickPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => handleSend(prompt)}
                    disabled={loading || streaming}
                    className="border-2 border-[var(--border)] bg-[var(--background-elevated)] px-3 py-2.5 font-body text-sm text-left text-[var(--foreground)] transition-colors duration-150 hover:bg-[var(--primary)] hover:text-[#000000] disabled:opacity-40 cursor-pointer"
                    style={{ boxShadow: "2px 2px 0 var(--border)" }}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-6">
          {messages.map((m) => (
            <ChatMessageBubble key={m.id} message={m} />
          ))}
          {loading && <TypingIndicator />}

          {contactState !== "idle" && (
            <div
              className="border-2 border-[var(--border)] bg-[var(--surface)] p-5"
              style={{ boxShadow: "5px 5px 0 var(--border)" }}
            >
              {contactState === "sent" ? (
                <p className="font-body text-sm font-semibold text-[var(--foreground)] uppercase tracking-wide">
                  Your question has been sent! You&apos;ll hear back soon.
                </p>
              ) : contactState === "error" ? (
                <p className="font-body text-sm font-semibold text-[var(--secondary)] uppercase tracking-wide">
                  Failed to send. Please try again or reach out directly.
                </p>
              ) : (
                <>
                  <p className="mb-4 font-body text-sm font-semibold text-[var(--foreground-muted)] uppercase tracking-wide">
                    I don&apos;t have that information yet. Leave your details and I&apos;ll pass your question along.
                  </p>
                  <form onSubmit={handleContactSubmit} className="flex flex-col gap-3">
                    <input
                      type="text"
                      placeholder="Your name"
                      value={contactName}
                      onChange={(e) => setContactName(e.target.value)}
                      disabled={contactState === "sending"}
                      className="border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:border-[var(--primary)] disabled:opacity-50"
                    />
                    <input
                      type="email"
                      placeholder="Your email"
                      value={contactEmail}
                      onChange={(e) => setContactEmail(e.target.value)}
                      disabled={contactState === "sending"}
                      className="border-2 border-[var(--border)] bg-[var(--background)] px-3 py-2 font-body text-sm text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none focus:border-[var(--primary)] disabled:opacity-50"
                    />
                    {contactError && (
                      <p className="font-body text-xs font-semibold text-[var(--secondary)] uppercase">{contactError}</p>
                    )}
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        disabled={contactState === "sending"}
                        className="border-2 border-[var(--border)] bg-[var(--primary)] px-4 py-2 font-body text-sm font-bold uppercase tracking-wide text-[#000000] transition-colors hover:bg-[var(--primary-hover)] disabled:opacity-50 cursor-pointer"
                      >
                        {contactState === "sending" ? "Sending…" : "Send question"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setContactState("idle")}
                        disabled={contactState === "sending"}
                        className="border-2 border-[var(--border)] bg-transparent px-4 py-2 font-body text-sm font-bold uppercase tracking-wide text-[var(--foreground-muted)] transition-colors hover:bg-[var(--background-elevated)] hover:text-[var(--foreground)] disabled:opacity-50 cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  </form>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="shrink-0 border-t-2 border-[var(--border)] bg-[var(--background)] p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={handleSend}
            disabled={loading || streaming}
            placeholder={`Ask anything about ${ownerName}…`}
          />
        </div>
      </div>
    </div>
  );
}
