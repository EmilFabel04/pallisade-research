"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { ensureSeeded } from "@/lib/artefacts";
import { SEED_ARTEFACTS } from "@/lib/seed";
import { PlatformShell } from "./_shell/PlatformShell";

export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);
  // Seed demo artefacts once for the whole platform (not just /artefacts) so the
  // Dashboard's recent-activity/pinned cards populate on first load.
  useEffect(() => ensureSeeded(SEED_ARTEFACTS), []);
  if (loading || !user) return null;
  return <PlatformShell>{children}</PlatformShell>;
}
