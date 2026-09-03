import type { LucideIcon } from "lucide-react";
import {
  Home,
  FolderKanban,
  LayoutPanelLeft,
  Bot,
  Bug,
  BookOpen,
  Settings,
  MoreHorizontal,
} from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  mobile?: boolean;
}

export const navItems: NavItem[] = [
  { href: "/", label: "Today", icon: Home, mobile: true },
  { href: "/projects", label: "Projects", icon: FolderKanban, mobile: true },
  { href: "/workspace", label: "Workspace", icon: LayoutPanelLeft, mobile: true },
  { href: "/agent", label: "Agent", icon: Bot },
  { href: "/knowledge", label: "Knowledge", icon: BookOpen },
  { href: "/settings", label: "Settings", icon: Settings },
];

export const moreNavItems: NavItem[] = [
  { href: "/start", label: "Start Center", icon: MoreHorizontal },
  { href: "/debug", label: "Debug", icon: Bug },
  { href: "/tools", label: "工具", icon: MoreHorizontal },
  { href: "/benchmark", label: "Benchmark", icon: MoreHorizontal },
  { href: "/history", label: "历史", icon: MoreHorizontal },
  { href: "/ioc", label: "IOC", icon: MoreHorizontal },
  { href: "/mcu", label: "MCU", icon: MoreHorizontal },
  { href: "/skills", label: "Skills", icon: MoreHorizontal },
  { href: "/memory/errors", label: "Error Memory", icon: MoreHorizontal },
];

export const IDE_ROUTES = ["/workspace", "/agent", "/code", "/debug"];

export function isIdeRoute(pathname: string): boolean {
  return IDE_ROUTES.some((r) => pathname === r || pathname.startsWith(`${r}/`));
}
