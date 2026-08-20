import type { RemoteModelInfo } from "@/lib/types";

export type RemoteProviderKind = "ollama" | "openrouter" | "gigachat";

export type GigachatAuthMode = "client" | "api_key";

export type OllamaDraft = {
  base_url: string;
  model: string;
};

export type OpenRouterDraft = {
  base_url: string;
  api_key: string;
  model: string;
};

export type GigachatDraft = {
  authMode: GigachatAuthMode;
  clientId: string;
  clientSecret: string;
  credentials: string;
  scope: string;
  base_url: string;
  auth_url: string;
  model: string;
  verify_ssl: boolean;
};

export type SecretHints = {
  apiKeyConfigured?: boolean;
  apiKeyMasked?: string | null;
  credentialsConfigured?: boolean;
  credentialsMasked?: string | null;
};

export type ModelsQueryState = {
  items: RemoteModelInfo[];
  loading: boolean;
  error: string | null;
  emptyHint: string;
  onRefresh: () => void;
};
