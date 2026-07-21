"use client";

import { useEffect, useState, type FormEvent } from "react";
import { ApiError } from "@/lib/api";
import { Badge, Button, EmptyState, Field, Input, SectionCard, Skeleton, toast } from "@/app/_ui";
import {
  type CatalogEntry,
  type Connection,
  createConnection,
  deleteConnection,
  getCatalog,
  listConnections,
  testConnection,
} from "@/lib/connections";

function humanize(id: string): string {
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function errorDetail(e: unknown): string {
  if (e instanceof ApiError) {
    const body = e.body as { detail?: string } | null;
    if (body && typeof body.detail === "string") return body.detail;
    if (e.status === 403) return "Admin access required.";
    return `Request failed (${e.status})`;
  }
  return e instanceof Error ? e.message : "Something went wrong.";
}

function statusTone(status: Connection["status"]): "ok" | "err" | "neutral" {
  if (status === "connected") return "ok";
  if (status === "error") return "err";
  return "neutral";
}

export function ConnectorsPanel() {
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedType, setSelectedType] = useState("");
  const [label, setLabel] = useState("");
  const [credentials, setCredentials] = useState("");
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [testingId, setTestingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setLoadError(null);
    try {
      const [cat, conns] = await Promise.all([getCatalog(), listConnections()]);
      setCatalog(cat);
      setConnections(conns);
    } catch (e) {
      setLoadError(errorDetail(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function refreshConnections() {
    try {
      setConnections(await listConnections());
    } catch (e) {
      toast.error(errorDetail(e));
    }
  }

  function resetForm() {
    setSelectedType("");
    setLabel("");
    setCredentials("");
    setConfigValues({});
    setAddError(null);
  }

  const activeEntry = catalog.find((c) => c.type_id === selectedType) ?? null;
  const missingRequiredConfig = activeEntry?.config_fields.some(
    (f) => f.required && !(configValues[f.name] ?? "").trim(),
  );

  async function handleCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!activeEntry) return;
    setSubmitting(true);
    setAddError(null);
    try {
      await createConnection({
        connector_type: activeEntry.type_id,
        label: label.trim() || activeEntry.type_id,
        credentials: activeEntry.requires_credentials ? credentials.trim() || undefined : undefined,
        config: configValues,
      });
      await refreshConnections();
      resetForm();
      toast.success("Connector added");
    } catch (e) {
      setAddError(errorDetail(e));
      toast.error(errorDetail(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      const result = await testConnection(id);
      await refreshConnections();
      if (result.status === "connected") {
        toast.success(result.result.detail || "Connection healthy");
      } else {
        toast.error(result.result.detail || "Connection test failed");
      }
    } catch (e) {
      toast.error(errorDetail(e));
    } finally {
      setTestingId(null);
    }
  }

  async function handleDelete(c: Connection) {
    setDeletingId(c.id);
    try {
      await deleteConnection(c.id);
      await refreshConnections();
      toast.success(`${c.label} removed`);
    } catch (e) {
      toast.error(errorDetail(e));
    } finally {
      setDeletingId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (loadError) {
    return (
      <EmptyState
        title="Could not load connectors"
        hint={loadError}
        action={
          <Button variant="secondary" onClick={load}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div className="space-y-6">
      <SectionCard title="Connected">
        {connections.length === 0 ? (
          <EmptyState
            title="No connectors yet"
            hint="Add one below to bring outside data into the platform."
          />
        ) : (
          <div className="space-y-3">
            {connections.map((c) => (
              <div
                key={c.id}
                className="rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-[var(--color-fg)]">{c.label}</span>
                      <Badge tone="neutral">{humanize(c.connector_type)}</Badge>
                      <Badge tone={statusTone(c.status)}>{c.status}</Badge>
                    </div>
                    <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                      {c.credentials_set ? "credentials set" : "no credentials"}
                      {c.serves.length > 0 ? ` • serves: ${c.serves.join(", ")}` : ""}
                    </p>
                    {c.status === "error" && c.last_error && (
                      <p className="mt-2 text-[12px] text-[var(--color-negative)]">
                        {c.last_error}
                      </p>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Button
                      variant="secondary"
                      onClick={() => handleTest(c.id)}
                      disabled={testingId === c.id}
                    >
                      {testingId === c.id ? "Testing…" : "Test"}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => handleDelete(c)}
                      disabled={deletingId === c.id}
                    >
                      {deletingId === c.id ? "Removing…" : "Delete"}
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </SectionCard>

      <SectionCard title="Add a connector">
        {catalog.length === 0 ? (
          <p className="text-sm text-[var(--color-fg-muted)]">No connector types available.</p>
        ) : (
          <form onSubmit={handleCreate} className="space-y-4">
            <Field label="Connector type">
              <select
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value);
                  setCredentials("");
                  setConfigValues({});
                  setAddError(null);
                }}
                className="w-full rounded-md bg-[var(--color-surface-2)] border border-[var(--color-border)] px-3 py-2 text-sm text-[var(--color-fg)] outline-none transition focus:border-[var(--color-accent)] focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-0"
              >
                <option value="">Select a connector…</option>
                {catalog.map((entry) => (
                  <option key={entry.type_id} value={entry.type_id}>
                    {humanize(entry.type_id)}
                  </option>
                ))}
              </select>
            </Field>

            {activeEntry && (
              <>
                <Field label="Label">
                  <Input
                    value={label}
                    onChange={(e) => setLabel(e.target.value)}
                    placeholder={humanize(activeEntry.type_id)}
                  />
                </Field>

                {activeEntry.requires_credentials && (
                  <Field label="Credentials">
                    <Input
                      type="password"
                      value={credentials}
                      onChange={(e) => setCredentials(e.target.value)}
                      placeholder="API key"
                    />
                  </Field>
                )}

                {activeEntry.config_fields.map((f) => (
                  <Field key={f.name} label={`${f.label}${f.required ? " *" : ""}`}>
                    <Input
                      value={configValues[f.name] ?? ""}
                      onChange={(e) =>
                        setConfigValues((cur) => ({ ...cur, [f.name]: e.target.value }))
                      }
                      placeholder={f.label}
                    />
                  </Field>
                ))}

                {addError && <p className="text-[12px] text-[var(--color-negative)]">{addError}</p>}

                <Button type="submit" disabled={submitting || !!missingRequiredConfig}>
                  {submitting ? "Creating…" : "Create"}
                </Button>
              </>
            )}
          </form>
        )}
      </SectionCard>
    </div>
  );
}
