export type ModelCapability =
  | "text"
  | "vision"
  | "reasoning"
  | "image"
  | "audio"
  | "embedding"
  | "tools";

export type ModelStatus = "active" | "deprecated" | "disabled";

export interface Model {
  id: string;
  name: string;
  providerId: string;
  alias: string;
  inputPrice: number;
  outputPrice: number;
  context: number;
  capabilities: ModelCapability[];
  status: ModelStatus;
  preferredProviderId: string;
  todayCalls: number;
}

export interface ModelInput {
  name: string;
  providerId: string;
  alias: string;
  inputPrice: number;
  outputPrice: number;
  context: number;
  capabilities: ModelCapability[];
  preferredProviderId: string;
  status?: ModelStatus;
}
