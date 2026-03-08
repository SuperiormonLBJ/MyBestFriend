"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";

export type FrontendConfig = {
  app_name: string;
  chat_title: string;
  chat_subtitle: string;
  input_placeholder: string;
  empty_state_hint: string;
  empty_state_examples: string;
};

export type ModelsConfig = {
  embedding_model?: string;
  generator_model?: string;
  llm_model?: string;
  rewrite_model?: string;
  reranker_model?: string;
  evaluator_model?: string;
};

export type FullConfig = FrontendConfig &
  ModelsConfig & {
    recipient_email?: string;
  };

const defaultConfig: FrontendConfig = {
  app_name: "MyBestFriend",
  chat_title: "Digital Twin",
  chat_subtitle:
    "Ask anything about me — career, projects, hobbies, or daily life",
  input_placeholder: "Ask anything about me...",
  empty_state_hint: "Type a question or use the microphone for voice input",
  empty_state_examples:
    'Try: "What is Beiji\'s experience at UOB?" or "Tell me about his hobbies"',
};

type ConfigContextType = {
  config: FullConfig;
  isLoading: boolean;
  refetch: () => Promise<void>;
};

const ConfigContext = createContext<ConfigContextType | undefined>(undefined);

export function ConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<FullConfig>(defaultConfig);
  const [isLoading, setIsLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/config");
      if (res.ok) {
        const data = await res.json();
        setConfig((prev) => ({ ...prev, ...data }) as FullConfig);
      }
    } catch {
      // Keep defaults on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return (
    <ConfigContext.Provider value={{ config, isLoading, refetch: fetchConfig }}>
      {children}
    </ConfigContext.Provider>
  );
}

export function useConfig() {
  const ctx = useContext(ConfigContext);
  if (!ctx) throw new Error("useConfig must be used within ConfigProvider");
  return ctx;
}
