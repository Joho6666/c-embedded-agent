export interface SettingsState {
  general: {
    orgName: string;
    timezone: string;
    language: string;
  };
  gateway: {
    baseUrl: string;
    defaultTimeoutMs: number;
    retry: number;
    streamEnabled: boolean;
  };
  security: {
    ipAllowlist: string;
    requireHttps: boolean;
    keyPrefix: string;
  };
  billing: {
    currency: string;
    markup: number;
  };
  notification: {
    email: string;
    webhook: string;
    onError: boolean;
    onBudget: boolean;
  };
  database: {
    driver: string;
    host: string;
  };
  logs: {
    retentionDays: number;
    sampleRate: number;
  };
  advanced: {
    debug: boolean;
    maxConcurrency: number;
  };
}
