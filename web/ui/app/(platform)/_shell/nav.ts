export interface NavItem {
  href: string;
  label: string;
  glyph: string; // single glyph char, matching the existing RailItem language
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard", label: "Dashboard", glyph: "◼" },
  { href: "/watchlist", label: "Watchlist", glyph: "▤" },
  { href: "/research", label: "Research", glyph: "›_" },
  { href: "/agents", label: "Agents", glyph: "◎" },
  { href: "/debate", label: "Debate", glyph: "⇄" },
  { href: "/artefacts", label: "Artefacts", glyph: "◇" },
  { href: "/checks", label: "Checks", glyph: "✓" },
  { href: "/settings", label: "Settings", glyph: "⚙" },
];

// URL prefixes owned by the platform shell — legacy Shell bypasses chrome here.
export const PLATFORM_PREFIXES = NAV_ITEMS.map((n) => n.href);
