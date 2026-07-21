import { api } from "./api";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type DocumentStatus = "pending" | "parsing" | "embedding" | "ready" | "failed";

export interface DocumentRow {
  id: string;
  deal_id: string;
  filename: string;
  content_type: string;
  byte_size: number;
  source_kind: string;
  status: DocumentStatus;
  page_count: number | null;
  error_message: string | null;
  uploader_id: string;
  created_at: string;
  updated_at: string;
}

export async function listDocuments(dealId: string): Promise<DocumentRow[]> {
  const data = await api<{ documents: DocumentRow[] }>(`/api/deals/${dealId}/documents`);
  return data.documents;
}

export async function uploadDocument(dealId: string, file: File): Promise<DocumentRow> {
  // Multipart upload — can't use the JSON-only api() helper.
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/api/deals/${dealId}/documents`, {
    method: "POST",
    credentials: "include",
    body: fd,
  });
  if (res.status === 409) throw new Error("This file is already attached to the deal.");
  if (res.status === 413) throw new Error("File is too large.");
  if (res.status === 415) throw new Error("Unsupported file type.");
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  return res.json();
}

export async function retryDocument(dealId: string, docId: string): Promise<DocumentRow> {
  return api<DocumentRow>(`/api/deals/${dealId}/documents/${docId}/retry`, {
    method: "POST",
  });
}

export async function deleteDocument(dealId: string, docId: string): Promise<void> {
  await api<void>(`/api/deals/${dealId}/documents/${docId}`, { method: "DELETE" });
}
