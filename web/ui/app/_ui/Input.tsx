"use client";

import type { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...rest
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...rest}
      className={
        "w-full rounded-md bg-[var(--color-surface-2)] " +
        "border border-[var(--color-border)] px-3 py-2 text-sm " +
        "text-[var(--color-fg)] outline-none transition " +
        "focus:border-[var(--color-accent)] " +
        "focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-0 " +
        className
      }
    />
  );
}
