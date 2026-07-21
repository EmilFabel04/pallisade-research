"use client";

import { useRouter } from "next/navigation";

import { PageHeader } from "@/app/_ui";
import type { MemoCheck } from "@/lib/memoChecks";

import { NewCheckForm } from "./_ui/NewCheckForm";
import { ChecksList } from "./_ui/ChecksList";

export default function ChecksPage() {
  const router = useRouter();

  return (
    <div>
      <PageHeader
        title="Checks"
        subtitle="Check an IC memo's cited figures against your document corpus."
      />

      <NewCheckForm
        onCreated={(check: MemoCheck) => router.push(`/checks/${check.id}`)}
      />

      <div className="mt-8">
        <ChecksList />
      </div>
    </div>
  );
}
