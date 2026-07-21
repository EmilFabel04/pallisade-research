"use client";

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={`pallisade-skeleton rounded-md ${className}`}
    />
  );
}
