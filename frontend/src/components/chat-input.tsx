"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff, Loader2 } from "lucide-react";

type ChatInputProps = {
  onSend: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
};

export function ChatInput({
  onSend,
  disabled = false,
  placeholder = "Ask anything about me...",
}: ChatInputProps) {
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const api = window.SpeechRecognition ?? window.webkitSpeechRecognition;
      setSpeechSupported(!!api);
    }
  }, []);

  const startListening = () => {
    if (typeof window === "undefined") return;
    const SpeechRecognitionAPI = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) return;
    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = event.results[event.results.length - 1][0].transcript;
      setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
    };
    recognition.onerror = () => setIsListening(false);

    recognition.start();
    recognitionRef.current = recognition;
  };

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
    setIsListening(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 border-2 border-[var(--border)] bg-[var(--background-elevated)] p-2 transition-colors duration-200"
      style={{ boxShadow: "4px 4px 0 var(--border)" }}
    >
      <label htmlFor="chat-input" className="sr-only">
        Your question
      </label>
      <textarea
        id="chat-input"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
          }
        }}
        placeholder={placeholder}
        rows={1}
        disabled={disabled}
        className="min-h-[44px] max-h-32 flex-1 resize-none border-0 bg-transparent px-4 py-3 font-body text-base text-[var(--foreground)] placeholder:text-[var(--foreground-muted)] focus:outline-none disabled:opacity-50"
        aria-label="Type your message"
      />
      <div className="flex shrink-0 gap-1">
        {speechSupported && (
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            aria-label={isListening ? "Stop listening" : "Start voice input"}
            className={`flex h-10 w-10 items-center justify-center border-2 border-[var(--border)] transition-colors duration-200 cursor-pointer ${
              isListening
                ? "bg-[var(--secondary)] text-white"
                : "bg-transparent text-[var(--foreground-muted)] hover:bg-[var(--primary)] hover:text-[var(--foreground)]"
            }`}
          >
            {isListening ? (
              <MicOff className="h-5 w-5" strokeWidth={2.5} />
            ) : (
              <Mic className="h-5 w-5" strokeWidth={2.5} />
            )}
          </button>
        )}
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          aria-label="Send message"
          className="flex h-10 w-10 items-center justify-center border-2 border-[var(--border)] bg-[var(--primary)] text-[#000000] font-semibold transition-colors duration-200 hover:bg-[var(--primary-hover)] disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {disabled ? (
            <Loader2 className="h-5 w-5 animate-spin" strokeWidth={2.5} />
          ) : (
            <Send className="h-5 w-5" strokeWidth={2.5} />
          )}
        </button>
      </div>
    </form>
  );
}
