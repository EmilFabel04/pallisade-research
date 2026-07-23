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
      className={`elevated rounded-lg border border-[var(--color-border)] p-5 ${className}`}
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
