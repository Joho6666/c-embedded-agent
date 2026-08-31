export type ToolConnection = "connected" | "disconnected" | "error";

export interface AgentTool {
  id: string;
  name: string;
  category:
    | "Compiler"
    | "Code Intelligence"
    | "Static Analysis"
    | "Testing"
    | "Hardware"
    | "Serial"
    | "Git"
    | "Generator";
  status: ToolConnection;
  version?: string;
  executable?: string;
  capabilities: string[];
  permissions: Array<"read" | "write" | "flash" | "erase" | "debug">;
  lastChecked: string;
  detail?: string;
}

export type ToolItem = AgentTool & { group: AgentTool["category"] };
