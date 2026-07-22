"use client";

import { PageHeader, Tabs } from "@/app/_ui";
import { ConnectorsPanel } from "./ConnectorsPanel";
import { DocsPanel } from "./DocsPanel";

export function SettingsTabs() {
  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage data connectors and your document corpus."
      />

      <Tabs defaultValue="connectors">
        <Tabs.List aria-label="Settings sections">
          <Tabs.Trigger value="connectors">Connectors</Tabs.Trigger>
          <Tabs.Trigger value="docs">Docs</Tabs.Trigger>
        </Tabs.List>
        <Tabs.Panel value="connectors">
          <ConnectorsPanel />
        </Tabs.Panel>
        <Tabs.Panel value="docs">
          <DocsPanel />
        </Tabs.Panel>
      </Tabs>
    </div>
  );
}
