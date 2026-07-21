import { api } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface OrgDocument {
  id: string;
  org_id: string | null;
  filename: string;
  content_type: string;
  byte_size: number;
  source_kind: string;
  status: "pending" | "parsing" | "embedding" | "ready" | "failed";
  page_count: number | null;
  error_message: string | null;
  uploader_id: string;
  created_at: string;
  updated_at: string;
}

export const listOrgDocuments = () =>
  api<{ documents: OrgDocument[] }>("/api/org/documents");

export async function uploadOrgDocument(file: File): Promise<OrgDocument> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/api/org/documents`, {
    method: "POST", credentials: "include", body: fd,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `upload failed (${res.status})`);
  }
  return res.json();
}

export const deleteOrgDocument = (id: string) =>
  api<void>(`/api/org/documents/${id}`, { method: "DELETE" });
