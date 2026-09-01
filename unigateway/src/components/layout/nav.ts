import type { LucideIcon } from "lucide-react";
import {
  Activity,
  BarChart3,
  GitBranch,
  KeyRound,
  LayoutDashboard,
  ScrollText,
  Server,
  Settings,
  Boxes,
  Users,
} from "lucide-react";
import { t } from "@/lib/i18n";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  mobile?: boolean;
}

export const navItems: NavItem[] = [
  { href: "/", label: t.nav.dashboard, icon: LayoutDashboard, mobile: true },
  { href: "/providers", label: t.nav.providers, icon: Server, mobile: true },
  { href: "/models", label: t.nav.models, icon: Boxes, mobile: true },
  { href: "/routing", label: t.nav.routing, icon: GitBranch, mobile: true },
  { href: "/api-keys", label: t.nav.keys, icon: KeyRound },
  { href: "/logs", label: t.nav.logs, icon: ScrollText },
  { href: "/analytics", label: t.nav.analytics, icon: BarChart3 },
  { href: "/users", label: t.nav.users, icon: Users },
  { href: "/monitor", label: t.nav.monitor, icon: Activity },
  { href: "/settings", label: t.nav.settings, icon: Settings },
];
