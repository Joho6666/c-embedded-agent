export type AuthScheme =
  | "api_key"
  | "bearer"
  | "oauth"
  | "service_account"
  | "project"
  | "env"
  | "local"
  | "custom_header";

export type EndpointKind =
  | "chat"
  | "responses"
  | "embeddings"
  | "images"
  | "audio"
  | "rerank"
  | "agent";

export type CapabilityKind =
  | "chat"
  | "responses"
  | "tools"
  | "vision"
  | "image"
  | "embedding"
  | "audio"
  | "agent"
  | "coding"
  | "reasoning"
  | "streaming"
  | "json";

export type ProviderStatus = "operational" | "degraded" | "partial_outage" | "down" | "offline";

export type FieldType =
  | "text"
  | "password"
  | "url"
  | "select"
  | "number"
  | "textarea"
  | "headers"
  | "checkbox";

export interface FormFieldOption {
  value: string;
  label: string;
}

export interface FormField {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  placeholder?: string;
  group?: string;
  help?: string;
  options?: FormFieldOption[];
}

export interface ProviderDescriptor {
  id: string;
  name: string;
  family: string;
  color: string;
  mark: string;
  local?: boolean;
  builtin: boolean;
  authSchemes: AuthScheme[];
  endpoints: EndpointKind[];
  capabilities: CapabilityKind[];
  regions?: string[];
  formFields: FormField[];
  defaultBaseUrl?: string;
  docsHint?: string;
}

export interface Provider {
  id: string;
  descriptorId: string;
  name: string;
  family: string;
  status: ProviderStatus;
  color: string;
  mark: string;
  local?: boolean;
  custom?: boolean;
  baseUrl?: string;
  regions?: string[];
  capabilities: CapabilityKind[];
  endpoints: EndpointKind[];
  authSchemes: AuthScheme[];
  credentialCount: number;
  modelCount: number;
  requestsToday: number;
  tokensToday: number;
  costToday: number;
  latencyMs: number;
  successRate: number;
  host?: string;
  gpu?: string;
}
