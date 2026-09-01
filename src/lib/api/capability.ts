export class BackendUnavailableError extends Error {
  status: number;
  path: string;

  constructor(status: number, path: string, message?: string) {
    super(message ?? (status === 404 ? "Backend Not Implemented" : `Backend capability unavailable (${status})`));
    this.name = "BackendUnavailableError";
    this.status = status;
    this.path = path;
  }
}

export function unavailableReason(err: unknown): string {
  if (err instanceof BackendUnavailableError) return err.message;
  if (err instanceof Error) {
    if (/404/.test(err.message)) return "Backend Not Implemented";
    return err.message || "Backend capability unavailable";
  }
  return "Backend capability unavailable";
}
