"use client";

import { SectionCard, Segmented } from "@/app/_ui";
import { useTheme } from "@/lib/theme";

export function AppearancePanel() {
  const { theme, setTheme } = useTheme();
  return (
    <SectionCard title="Appearance">
      <div className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-[var(--color-fg)]">Theme</p>
            <p className="text-xs text-[var(--color-fg-muted)]">
              Applies instantly and is saved to this browser.
            </p>
          </div>
          <Segmented
            aria-label="Theme"
            value={theme}
            onChange={setTheme}
            options={[
              { value: "dark", label: "Dark" },
              { value: "light", label: "Light" },
            ]}
          />
        </div>

        <div className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-2)] p-3">
          <span className="h-8 w-8 shrink-0 rounded-md bg-[var(--color-accent)]" />
          <div className="min-w-0">
            <p className="text-sm text-[var(--color-fg)]">Aa — Pallisade</p>
            <p className="text-xs text-[var(--color-fg-muted)]">Preview of the current theme.</p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
