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
  owner_name: string;
};

export type ModelsConfig = {
  embedding_model?: string;
  generator_model?: string;
  llm_model?: string;
  rewrite_model?: string;
  reranker_model?: string;
  evaluator_model?: string;
};

export type RetrievalConfig = {
  hybrid_search_enabled?: boolean;
  lexical_weight?: number;
  metadata_filter_enabled?: boolean;
  self_check_enabled?: boolean;
  multi_step_enabled?: boolean;
  use_graph?: boolean;
  use_multi_agent?: boolean;
  multi_agent_token_budget?: number;
  multi_agent_parallel?: boolean;
  multi_agent_log_traces?: boolean;
};

export type FullConfig = FrontendConfig &
  ModelsConfig &
  RetrievalConfig & {
    recipient_email?: string;
    admin_api_key?: string;
  };

const defaultConfig: FrontendConfig = {
  app_name: "MyBestFriend",
  owner_name: "Beiji",
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
