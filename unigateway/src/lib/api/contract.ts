/**
 * UniGateway console talks to `api` in client.ts.
 *
 * Current adapter: mock (`lib/mock/store.ts`).
 *
 * Existing FastAPI admin surface (backend/app/api/admin.py) is a different shape:
 *   GET/POST /admin/providers
 *   GET/POST /admin/virtual-models  { slug, candidates, strategy, fallbackChain }
 *   GET/POST /admin/keys
 *
 * Console RoutePolicy / User / Plan types are richer than that admin schema.
 * Do not point this UI at localhost or private IPs. A remote adapter should
 * only allow http/https public hosts, and map fields explicitly.
 */
export const ADMIN_CONTRACT = {
  providers: "/admin/providers",
  virtualModels: "/admin/virtual-models",
  keys: "/admin/keys",
  logs: "/admin/logs",
} as const;
