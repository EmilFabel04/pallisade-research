"use client";

import type { ButtonHTMLAttributes } from "react";
import type { LucideIcon } from "lucide-react";

type IconButtonVariant = "ghost" | "primary" | "accent";
type IconButtonSize = "sm" | "md";

const sizeMap: Record<IconButtonSize, { box: string; icon: number }> = {
  sm: { box: "h-7 w-7", icon: 14 },
  md: { box: "h-9 w-9", icon: 18 },
};

const variantMap: Record<IconButtonVariant, string> = {
  ghost:
    "text-[var(--color-fg-dim)] border border-[var(--color-border)] " +
    "hover:text-[var(--color-fg)] hover:border-[var(--color-accent)]",
  primary: "bg-[var(--color-accent)] text-white border border-transparent hover:brightness-110",
  accent:
    "text-[var(--color-accent)] bg-[var(--color-accent-soft)] " +
    "border border-[var(--color-accent)] hover:brightness-110",
};

export function IconButton({
  icon: Icon,
  label,
  size = "md",
  variant = "ghost",
  className = "",
  ...rest
}: {
  icon: LucideIcon;
  label: string;
  size?: IconButtonSize;
  variant?: IconButtonVariant;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const s = sizeMap[size];
  return (
    <button
      {...rest}
      aria-label={label}
      title={label}
      className={`inline-flex shrink-0 items-center justify-center rounded-md transition-all duration-150 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed ${s.box} ${variantMap[variant]} ${className}`}
    >
      <Icon size={s.icon} strokeWidth={1.75} aria-hidden="true" />
    </button>
  );
}
