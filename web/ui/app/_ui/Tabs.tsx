"use client";

import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

function Root({
  defaultValue,
  value,
  onValueChange,
  className = "",
  children,
}: {
  defaultValue?: string;
  value?: string;
  onValueChange?: (v: string) => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <RadixTabs.Root
      defaultValue={defaultValue}
      value={value}
      onValueChange={onValueChange}
      className={className}
    >
      {children}
    </RadixTabs.Root>
  );
}

function List({
  className = "",
  children,
  "aria-label": ariaLabel,
}: {
  className?: string;
  children: ReactNode;
  "aria-label"?: string;
}) {
  return (
    <RadixTabs.List
      aria-label={ariaLabel}
      className={
        "flex border-b border-[var(--color-border)] " + className
      }
    >
      {children}
    </RadixTabs.List>
  );
}

function Trigger({
  value,
  className = "",
  children,
}: {
  value: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <RadixTabs.Trigger
      value={value}
      className={
        "px-3.5 py-2 font-mono text-[11px] uppercase tracking-wider " +
        "text-[var(--color-fg-muted)] border-b-2 border-transparent " +
        "transition hover:text-[var(--color-fg-dim)] " +
        "data-[state=active]:text-[var(--color-fg)] " +
        "data-[state=active]:border-[var(--color-accent)] " +
        className
      }
    >
      {children}
    </RadixTabs.Trigger>
  );
}

function Panel({
  value,
  className = "",
  children,
}: {
  value: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <RadixTabs.Content value={value} className={`pt-6 ${className}`}>
      {children}
    </RadixTabs.Content>
  );
}

export const Tabs = Object.assign(Root, { List, Trigger, Panel });
