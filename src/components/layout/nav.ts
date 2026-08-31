import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BookOpen,
  CircuitBoard,
  Gauge,
  HeartPulse,
  KeyRound,
  LayoutDashboard,
  Layers,
  Play,
  Route,
  ScrollText,
  Server,
  Settings,
  ShieldAlert,
  Wallet,
  Waypoints,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  group?: string;
}

export const navItems: NavItem[] = [
  { href: "/", label: "概览", icon: LayoutDashboard, group: "控制" },
  { href: "/providers", label: "Provider", icon: Server, group: "供给" },
  { href: "/credentials", label: "凭据池", icon: ShieldAlert, group: "供给" },
  { href: "/models", label: "模型中心", icon: Layers, group: "供给" },
  { href: "/virtual-models", label: "虚拟模型", icon: Waypoints, group: "路由" },
  { href: "/routing", label: "路由策略", icon: Route, group: "路由" },
  { href: "/api-keys", label: "API Keys", icon: KeyRound, group: "接入" },
  { href: "/requests", label: "请求日志", icon: ScrollText, group: "观测" },
  { href: "/usage", label: "用量与成本", icon: Activity, group: "观测" },
  { href: "/quota", label: "额度", icon: Wallet, group: "观测" },
  { href: "/health", label: "健康状态", icon: HeartPulse, group: "可靠性" },
  { href: "/circuit-breakers", label: "熔断中心", icon: CircuitBoard, group: "可靠性" },
  { href: "/playground", label: "API Playground", icon: Play, group: "开发" },
  { href: "/developer", label: "开发者接入", icon: BookOpen, group: "开发" },
  { href: "/settings", label: "系统设置", icon: Settings, group: "系统" },
];

export const commandItems = [
  ...navItems,
  { href: "/playground", label: "打开 Playground", icon: Play },
  { href: "/", label: "复制 Gateway URL", icon: Gauge },
];
