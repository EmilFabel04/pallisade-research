"use client";

export function SectionCard({
  title,
  className = "",
  children,
}: {
  title?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-5 shadow-[var(--shadow-card)] ${className}`}
    >
      {title && (
        <h2 className="mb-3 font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}
