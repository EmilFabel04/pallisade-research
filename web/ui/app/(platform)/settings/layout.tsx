import { PageHeader } from "@/app/_ui";
import { SettingsRail } from "./_ui/SettingsRail";

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Manage connectors, documents, appearance, and your account."
      />
      <div className="flex flex-col gap-6 md:flex-row">
        <aside className="md:w-[200px] md:shrink-0">
          <SettingsRail />
        </aside>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}
