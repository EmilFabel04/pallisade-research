"use client";

import { useState } from "react";
import { PageHeader } from "@/app/_ui";
import { ConnectorsPanel } from "./ConnectorsPanel";
import { DocsPanel } from "./DocsPanel";

type SettingsTab = "connectors" | "docs";

const TABS: { key: SettingsTab; label: string }[] = [
  { key: "connectors", label: "Connectors" },
  { key: "docs", label: "Docs" },
];

export function SettingsTabs() {
  const [tab, setTab] = useState<SettingsTab>("connectors");

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage data connectors and your document corpus."
      />

      <div className="mb-6 flex gap-2" role="tablist" aria-label="Settings sections">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={[
              "rounded-full border px-3 py-1 font-mono text-[9px] uppercase tracking-[0.16em] transition-all duration-150",
              tab === t.key
                ? "border-[var(--color-accent)] bg-[rgba(139,11,16,0.12)] text-[var(--color-fg)]"
                : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-fg-muted)] hover:text-[var(--color-fg-dim)]",
            ].join(" ")}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "connectors" ? <ConnectorsPanel /> : <DocsPanel />}
    </div>
  );
}
