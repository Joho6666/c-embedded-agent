import { mockDb } from "@/lib/mock/store";
import type {
  ApiKeyInput,
  LogQuery,
  ProviderInput,
  RouteStrategy,
  SettingsState,
  TimeRange,
} from "@/types";

/** Swap this module to a remote adapter when the real Gateway exists. */
export const api = {
  listProviders: () => mockDb.listProviders(),
  createProvider: (input: ProviderInput) => mockDb.createProvider(input),
  updateProvider: (...args: Parameters<typeof mockDb.updateProvider>) => mockDb.updateProvider(...args),
  deleteProvider: (id: string) => mockDb.deleteProvider(id),
  toggleProvider: (id: string) => mockDb.toggleProvider(id),
  testProvider: (id: string) => mockDb.testProvider(id),
  pullModels: (id: string) => mockDb.pullModels(id),
  queryBalance: (id: string) => mockDb.queryBalance(id),
  listModels: () => mockDb.listModels(),
  listRoutes: () => mockDb.listRoutes(),
  updateRoute: (id: string, strategy: RouteStrategy) => mockDb.updateRoute(id, strategy),
  listKeys: () => mockDb.listKeys(),
  createKey: (input: ApiKeyInput) => mockDb.createKey(input),
  disableKey: (id: string) => mockDb.disableKey(id),
  deleteKey: (id: string) => mockDb.deleteKey(id),
  regenerateKey: (id: string) => mockDb.regenerateKey(id),
  listLogs: (query?: LogQuery) => mockDb.listLogs(query),
  getDashboard: () => mockDb.getDashboard(),
  getAnalytics: (range: TimeRange) => mockDb.getAnalytics(range),
  listUsers: () => mockDb.listUsers(),
  getMonitor: () => mockDb.getMonitor(),
  getSettings: () => mockDb.getSettings(),
  saveSettings: (next: SettingsState) => mockDb.saveSettings(next),
};
