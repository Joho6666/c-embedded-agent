import type { LucideIcon } from "lucide-react";
import {
  Bot,
  FolderKanban,
  Files,
  Cpu,
  BookOpen,
  Wrench,
  FlaskConical,
  History,
  Settings,
  LayoutDashboard,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  mobile?: boolean;
}

export const navItems: NavItem[] = [
  { href: "/", label: "总览", icon: LayoutDashboard, mobile: true },
  { href: "/agent", label: "Agent", icon: Bot, mobile: true },
  { href: "/projects", label: "项目", icon: FolderKanban, mobile: true },
  { href: "/code", label: "文件", icon: Files },
  { href: "/mcu", label: "芯片", icon: Cpu },
  { href: "/knowledge", label: "知识库", icon: BookOpen },
  { href: "/tools", label: "工具", icon: Wrench },
  { href: "/testing", label: "测试", icon: FlaskConical },
  { href: "/history", label: "历史记录", icon: History },
  { href: "/settings", label: "设置", icon: Settings },
];
