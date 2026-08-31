import { sleep } from "@/lib/utils";
import { useGateway } from "@/lib/stores/gateway";
import type { ApiKeyInput, CredentialInput, UsageRange } from "@/types";
import { usageByRange } from "@/lib/mock";

const delay = () => sleep(180 + Math.random() * 220);

export const gatewayApi = {
  async listProviders() {
    await delay();
    return useGateway.getState().providers;
  },
  async testProvider(id: string) {
    await sleep(600);
    const p = useGateway.getState().providers.find((x) => x.id === id);
    return { ok: p?.status !== "down", latencyMs: p?.latencyMs ?? 0, message: p ? `${p.name} reachable` : "not found" };
  },
  async syncModels(id: string) {
    await sleep(700);
    const count = useGateway.getState().models.filter((m) => m.providerId === id).length;
    return { synced: count };
  },
  async testCredential(id: string) {
    await sleep(500);
    const c = useGateway.getState().credentials.find((x) => x.id === id);
    const ok = c && c.status !== "unauthorized" && c.status !== "disabled" && c.status !== "circuit_open";
    return { ok: Boolean(ok), message: ok ? "Connection OK" : c?.lastError ?? "failed" };
  },
  async addCredential(input: CredentialInput) {
    await delay();
    return useGateway.getState().addCredential(input);
  },
  async addKey(input: ApiKeyInput) {
    await delay();
    return useGateway.getState().addKey(input);
  },
  async usage(range: UsageRange) {
    await delay();
    return usageByRange[range];
  },
};
