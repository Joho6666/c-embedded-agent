import { beforeEach, describe, expect, it } from "vitest";
import { assignTask } from "./service";
import { useOsStore } from "@/lib/stores/os-store";

describe("OS assign", () => {
  beforeEach(() => {
    useOsStore.setState({
      projects: [],
      tasks: [],
      documents: [],
      activities: [],
      agents: useOsStore.getState().agents,
    });
    useOsStore.getState().ensureSeed();
  });

  it("rejects planned agents", async () => {
    const project = useOsStore.getState().createProject({ name: "P" });
    const task = useOsStore.getState().createTask(project.id, { title: "T" });
    await expect(assignTask(task.id, "codex")).rejects.toMatchObject({
      status: 409,
      code: "agent_unavailable",
    });
  });

  it("rejects c-agent without firmware workspace", async () => {
    const project = useOsStore.getState().createProject({ name: "P" });
    const task = useOsStore.getState().createTask(project.id, { title: "T" });
    await expect(assignTask(task.id, "c-agent")).rejects.toMatchObject({
      code: "no_firmware_workspace",
    });
  });

  it("does not fake a live run in DEMO even with firmware id", async () => {
    const project = useOsStore.getState().createProject({ name: "P", backendProjectId: "abc" });
    const task = useOsStore.getState().createTask(project.id, { title: "T" });
    await expect(assignTask(task.id, "c-agent")).rejects.toMatchObject({
      code: "live_required",
    });
  });
});
