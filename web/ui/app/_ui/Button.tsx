"use client";

import type { ButtonHTMLAttributes } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";

const buttonBase =
  "inline-flex items-center justify-center rounded-md px-5 py-2.5 font-mono " +
  "text-xs uppercase tracking-wider transition disabled:opacity-50 " +
  "disabled:cursor-not-allowed";

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
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }) {
  return (
    <button
      {...rest}
      className={`${buttonBase} ${buttonByVariant[variant]} ${className}`}
    />
  );
}
