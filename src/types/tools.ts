export type ToolConnection = "connected" | "disconnected" | "error";

export interface ToolItem {
  id: string;
  name: string;
  group:
    | "Compiler"
    | "Code Intelligence"
    | "Static Analysis"
    | "Testing"
    | "Hardware"
    | "Serial"
    | "Git";
  status: ToolConnection;
  detail?: string;
}
