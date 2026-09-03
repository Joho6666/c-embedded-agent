import type { AgentEventStatus, AgentEventType } from "@/types/events";
import type { AgentStatus } from "@/types/agent";

export const eventTypeLabel: Record<AgentEventType, string> = {
  reasoning: "推理",
  plan: "计划",
  knowledge_query: "检索知识",
  knowledge_result: "知识结果",
  tool_call: "调用工具",
  tool_result: "工具结果",
  file_read: "读取文件",
  file_write: "写入文件",
  file_diff: "代码补丁",
  compile: "编译",
  diagnostic: "诊断",
  test: "测试",
  flash: "烧录",
  serial: "串口",
  validation: "验证",
  approval: "待确认",
  error: "错误",
  pin_conflict: "引脚冲突",
  terminal: "终端",
  run_stopped: "已停止",
  build_result: "构建结果",
};

export const eventStatusLabel: Record<AgentEventStatus, string> = {
  pending: "待处理",
  running: "进行中",
  success: "成功",
  failed: "失败",
  cancelled: "已取消",
  waiting_approval: "等待确认",
};

export function agentStatusLabel(status: AgentStatus) {
  if (status === "waiting_approval") return "等待确认";
  if (status === "working") return "Agent 工作中";
  if (status === "ready") return "Agent 就绪";
  if (status === "error") return "出错";
  if (status === "stopped") return "已停止";
  return status;
}

export const toolGroupLabel: Record<string, string> = {
  Generator: "工程生成",
  Compiler: "编译器",
  "Code Intelligence": "代码智能",
  "Static Analysis": "静态分析",
  Testing: "测试",
  Hardware: "硬件",
  Serial: "串口",
  Git: "Git",
};

export const riskLabel: Record<string, string> = {
  safe: "安全",
  low: "低",
  medium: "中",
  high: "高",
};
