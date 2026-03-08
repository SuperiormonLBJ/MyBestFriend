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

export type FullConfig = FrontendConfig &
  ModelsConfig & {
    recipient_email?: string;
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
