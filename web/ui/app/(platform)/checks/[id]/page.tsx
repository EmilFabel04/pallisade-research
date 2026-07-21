"use client";

import { useParams } from "next/navigation";

import { CheckReport } from "./_ui/CheckReport";

export default function CheckReportPage() {
  const { id } = useParams<{ id: string }>();
  return <CheckReport id={id} />;
}
