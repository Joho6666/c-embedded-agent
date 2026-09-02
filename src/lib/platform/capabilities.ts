import type { ToolbarActionId } from "@/types/platform";
import type { PlatformDefinition } from "@/types/platform";
import { getPlatform } from "./catalog";

export function disabledReason(
  platform: PlatformDefinition | string,
  action: ToolbarActionId,
  liveMode: "live" | "demo" | "offline",
): string | null {
  const def = typeof platform === "string" ? getPlatform(platform) : platform;
  if (action === "stop") return null;
  if (action === "debug") return null;
  if (!def.toolbarActions.includes(action)) {
    return `当前平台暂不支持 ${actionLabel(action)}`;
  }
  if (!def.supported) {
    return `${def.label} 后端尚未实现（${def.statusNote}）`;
  }
  if (liveMode !== "live") {
    return liveMode === "offline" ? "后端离线" : "DEMO 模式不可执行真实构建 / 烧录";
  }
  return null;
}

export function actionLabel(action: ToolbarActionId): string {
  const map: Record<ToolbarActionId, string> = {
    build: "构建",
    run: "运行",
    flash: "烧录",
    debug: "调试",
    serial: "串口",
    validate: "验证",
    test: "测试",
    analyze: "分析",
    monitor: "Monitor",
    hex: "HEX",
    stop: "停止",
  };
  return map[action];
}
