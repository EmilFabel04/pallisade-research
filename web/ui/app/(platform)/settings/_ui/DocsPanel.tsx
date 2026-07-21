"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api";
import { Badge, Button, Card, EmptyState, SectionCard, Skeleton, toast } from "@/app/_ui";
import {
  type OrgDocument,
  deleteOrgDocument,
  listOrgDocuments,
  uploadOrgDocument,
} from "@/lib/orgDocuments";

const CLOUD_SOURCES = [
  { id: "google_drive", label: "Google Drive" },
  { id: "onedrive", label: "OneDrive" },
  { id: "sharepoint", label: "SharePoint" },
] as const;

function errorDetail(e: unknown): string {
  if (e instanceof ApiError) {
    const body = e.body as { detail?: string } | null;
    if (body && typeof body.detail === "string") return body.detail;
    return `Request failed (${e.status})`;
  }
  return e instanceof Error ? e.message : "Something went wrong.";
}

function statusTone(status: OrgDocument["status"]): "ok" | "err" | "info" {
  if (status === "ready") return "ok";
  if (status === "failed") return "err";
  return "info";
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocsPanel() {
  const [docs, setDocs] = useState<OrgDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    try {
      const { documents } = await listOrgDocuments();
      setDocs(documents);
      setLoadError(null);
    } catch (e) {
      setLoadError(errorDetail(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll while any row is non-terminal; stop once everything is ready/failed.
  useEffect(() => {
    const nonTerminal = docs.some((d) => d.status !== "ready" && d.status !== "failed");
    if (!nonTerminal) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [docs, refresh]);

  const onFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    for (const f of Array.from(files)) {
      try {
        await uploadOrgDocument(f);
      } catch (e) {
        toast.error(errorDetail(e));
      }
    }
    if (fileInput.current) fileInput.current.value = "";
    refresh();
  };

  const onDelete = async (doc: OrgDocument) => {
    if (!confirm(`Delete ${doc.filename}? This cannot be undone.`)) return;
    setDeletingId(doc.id);
    try {
      await deleteOrgDocument(doc.id);
      await refresh();
      toast.success(`${doc.filename} removed`);
    } catch (e) {
      toast.error(errorDetail(e));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <SectionCard title="Connect a source">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {CLOUD_SOURCES.map((s) => (
            <Card key={s.id} className="flex items-center justify-between gap-3">
              <span className="text-sm text-[var(--color-fg)]">{s.label}</span>
              <div className="flex items-center gap-2">
                <Badge tone="info">Preview</Badge>
                <Button variant="secondary" disabled>
                  Connect
                </Button>
              </div>
            </Card>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-[var(--color-fg-muted)]">
          Cloud sync is coming soon — upload files manually below for now.
        </p>
      </SectionCard>

      <SectionCard title="Upload">
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            onFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInput.current?.click()}
          className="cursor-pointer rounded-md border border-dashed border-[var(--color-border)] p-10 text-center hover:border-[var(--color-fg-muted)]"
        >
          <p className="text-sm text-[var(--color-fg-dim)]">Drop files here, or click to upload</p>
          <p className="mt-1 text-xs text-[var(--color-fg-muted)]">PDF or .xlsx</p>
          <input
            ref={fileInput}
            type="file"
            multiple
            hidden
            accept=".pdf,application/pdf,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => onFiles(e.target.files)}
          />
        </div>
      </SectionCard>

      <SectionCard title="Corpus">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : loadError ? (
          <EmptyState
            title="Could not load documents"
            hint={loadError}
            action={
              <Button variant="secondary" onClick={refresh}>
                Retry
              </Button>
            }
          />
        ) : docs.length === 0 ? (
          <EmptyState title="No documents in your corpus yet" />
        ) : (
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--color-border)] text-left text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
              <tr>
                <th className="py-2">Filename</th>
                <th className="py-2">Source</th>
                <th className="py-2">Status</th>
                <th className="py-2">Size</th>
                <th className="py-2">Uploaded</th>
                <th className="py-2"></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2">{d.filename}</td>
                  <td className="py-2 text-[var(--color-fg-muted)]">{d.source_kind}</td>
                  <td className="py-2">
                    <Badge tone={statusTone(d.status)}>{d.status}</Badge>
                    {d.status === "failed" && d.error_message && (
                      <span className="ml-2 text-xs text-[var(--color-negative)]">
                        {d.error_message}
                      </span>
                    )}
                  </td>
                  <td className="py-2 text-[var(--color-fg-muted)]">{formatBytes(d.byte_size)}</td>
                  <td className="py-2 text-[var(--color-fg-muted)]">
                    {new Date(d.created_at).toLocaleString()}
                  </td>
                  <td className="py-2 text-right">
                    <Button
                      variant="ghost"
                      onClick={() => onDelete(d)}
                      disabled={deletingId === d.id}
                    >
                      {deletingId === d.id ? "Removing…" : "Delete"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </SectionCard>
    </div>
  );
}
