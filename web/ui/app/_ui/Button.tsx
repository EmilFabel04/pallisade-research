"use client";

import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md";

const buttonBase =
  "inline-flex items-center justify-center rounded-md font-mono " +
  "uppercase tracking-wider transition disabled:opacity-50 " +
  "disabled:cursor-not-allowed";

const buttonBySize: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-[11px]",
  md: "px-5 py-2.5 text-xs",
};

const buttonByVariant: Record<ButtonVariant, string> = {
  primary:
    "bg-[var(--color-accent)] text-white border border-transparent " +
    "hover:brightness-110 hover:shadow-[var(--shadow-accent-soft)]",
  secondary:
    "bg-transparent text-[var(--color-accent)] " +
    "border border-[var(--color-accent)] " +
    "hover:bg-[var(--color-accent-soft)]",
  ghost:
    "bg-transparent text-[var(--color-fg-dim)] " +
    "border border-[var(--color-border)] " +
    "hover:border-[var(--color-accent)] hover:text-[var(--color-fg)]",
};

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
}) {
  return (
    <button
      {...rest}
      className={`${buttonBase} ${buttonBySize[size]} ${buttonByVariant[variant]} ${className}`}
    />
  );
}
