import type { LucideIcon } from "lucide-react";
import { LayoutGrid, Eye, Terminal, MessagesSquare, Diamond, Settings } from "lucide-react";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutGrid },
  { href: "/watchlist", label: "Watchlist", icon: Eye },
  { href: "/research", label: "Research", icon: Terminal },
  { href: "/debate", label: "Debate", icon: MessagesSquare },
  { href: "/artefacts", label: "Artefacts", icon: Diamond },
  { href: "/settings", label: "Settings", icon: Settings },
];

// URL prefixes owned by the platform shell — legacy Shell bypasses chrome here.
export const PLATFORM_PREFIXES = NAV_ITEMS.map((n) => n.href);
