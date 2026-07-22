"use client";

import type { ReactNode } from "react";
import { useRouter } from "next/navigation";
import { Badge, Button, SectionCard, Skeleton } from "@/app/_ui";
import { useAuth } from "@/lib/auth";

function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--color-border)] py-3 last:border-0">
      <span className="font-mono text-[10px] uppercase tracking-widest text-[var(--color-fg-muted)]">
        {label}
      </span>
      <span className="text-sm text-[var(--color-fg)]">{value}</span>
    </div>
  );
}

export function AccountPanel() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) {
    return (
      <SectionCard title="Account">
        <Skeleton className="h-24 w-full" />
      </SectionCard>
    );
  }

  return (
    <SectionCard title="Account">
      <div>
        <Row label="Name" value={user.name} />
        <Row label="Email" value={user.email} />
        <Row
          label="Role"
          value={
            <Badge tone={user.role === "admin" ? "info" : "neutral"}>{user.role}</Badge>
          }
        />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/auth/change-password")}
        >
          Change password
        </Button>
        <Button variant="secondary" size="sm" onClick={() => logout()}>
          Sign out
        </Button>
      </div>
    </SectionCard>
  );
}
