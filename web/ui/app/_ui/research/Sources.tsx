"use client";

import { useEffect, useState, type FormEvent } from "react";
import { SERIF } from "@/lib/research-format";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Badge, EmptyState, toast } from "@/app/_ui";
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

function statusDot(status: Connection["status"]): string {
  return status === "connected"
    ? "bg-[var(--color-positive)]"
    : status === "error"
      ? "bg-[var(--color-negative)]"
      : "bg-[var(--color-fg-muted)]";
}

const inputClass =
  "w-full rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 font-mono text-xs text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-accent)] focus:outline-none";
const fieldLabelClass = "mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]";
const primaryBtnClass =
  "shrink-0 rounded-md bg-[var(--color-accent)] px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg)] transition-opacity hover:opacity-90 disabled:opacity-30";

export function Sources() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [connections, setConnections] = useState<Connection[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [credentials, setCredentials] = useState("");
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [serves, setServes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [testingId, setTestingId] = useState<string | null>(null);

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

  function selectType(typeId: string) {
    setSelectedType((cur) => (cur === typeId ? null : typeId));
    setAddError(null);
    setCredentials("");
    setConfigValues({});
    setServes([]);
    setLabel(typeId === selectedType ? "" : humanize(typeId));
  }

  function toggleServe(cap: string) {
    setServes((cur) => (cur.includes(cap) ? cur.filter((c) => c !== cap) : [...cur, cap]));
  }

  async function handleConnect(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!selectedType) return;
    setSubmitting(true);
    setAddError(null);
    try {
      const created = await createConnection({
        connector_type: selectedType,
        label: label.trim() || selectedType,
        credentials: credentials.trim() || undefined,
        config: configValues,
        serves,
      });
      try {
        await testConnection(created.id);
      } catch {
        // The connection was created; a failed test just leaves it "disconnected"/"error" —
        // the real status is reflected once we refresh below.
      }
      await refreshConnections();
      setSelectedType(null);
      setLabel("");
      setCredentials("");
      setConfigValues({});
      setServes([]);
      toast.success("Source connected");
    } catch (e) {
      setAddError(errorDetail(e));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleTest(id: string) {
    setTestingId(id);
    try {
      await testConnection(id);
      await refreshConnections();
    } catch (e) {
      toast.error(errorDetail(e));
    } finally {
      setTestingId(null);
    }
  }

  function handleDelete(c: Connection) {
    toast(`Remove ${c.label}?`, {
      description: "This disconnects the source. This cannot be undone.",
      duration: 8000,
      action: {
        label: "Remove",
        onClick: async () => {
          try {
            await deleteConnection(c.id);
            await refreshConnections();
          } catch (e) {
            toast.error(errorDetail(e));
          }
        },
      },
    });
  }

  const activeEntry = catalog.find((c) => c.type_id === selectedType) ?? null;
  const missingRequiredConfig = activeEntry?.config_fields.some(
    (f) => f.required && !(configValues[f.name] ?? "").trim(),
  );

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h2 className="text-2xl text-[var(--color-fg)]" style={SERIF}>
          Sources
        </h2>
        <p className="mt-1 text-sm text-[var(--color-fg-dim)]">
          Connect the data you already pay for. Each answer draws only from your connected
          sources — and cites every one.
        </p>
      </div>

      {loading ? (
        <p className="text-sm text-[var(--color-fg-muted)]">Loading sources…</p>
      ) : loadError ? (
        <EmptyState
          title="Could not load sources"
          hint={loadError}
          action={
            <button onClick={load} className={primaryBtnClass}>
              Retry
            </button>
          }
        />
      ) : (
        <>
          <div className="space-y-3">
            {connections.length === 0 ? (
              <EmptyState
                title="No sources connected yet"
                hint={isAdmin ? "Add one below." : "Ask an admin to connect a source."}
              />
            ) : (
              connections.map((c) => (
                <div
                  key={c.id}
                  className="rounded-[14px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 rounded-full ${statusDot(c.status)}`} />
                        <h3 className="text-base text-[var(--color-fg)]" style={SERIF}>
                          {c.label}
                        </h3>
                        <span className="rounded-full bg-[var(--color-accent-soft)] px-2 py-0.5 font-mono text-[9px] uppercase tracking-wider text-[var(--color-fg-dim)]">
                          {humanize(c.connector_type)}
                        </span>
                      </div>
                      <p className="mt-1 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                        {c.credentials_set ? "•••• set" : "no credentials"}
                      </p>
                      {c.serves.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1.5">
                          {c.serves.map((s) => (
                            <Badge key={s} tone="neutral">
                              {s}
                            </Badge>
                          ))}
                        </div>
                      )}
                      {c.status === "error" && c.last_error && (
                        <p className="mt-2 text-[12px] text-[var(--color-negative)]">{c.last_error}</p>
                      )}
                    </div>
                    <span className="shrink-0 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
                      {c.status}
                    </span>
                  </div>

                  {isAdmin && (
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={() => handleTest(c.id)}
                        disabled={testingId === c.id}
                        className={primaryBtnClass}
                      >
                        {testingId === c.id ? "Testing…" : "Test"}
                      </button>
                      <button
                        onClick={() => handleDelete(c)}
                        className="shrink-0 rounded-md border border-[var(--color-border)] px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-dim)] transition-colors hover:border-[var(--color-negative)] hover:text-[var(--color-negative)]"
                      >
                        Remove
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>

          {isAdmin ? (
            <div className="mt-6 rounded-[14px] border border-dashed border-[var(--color-border)] p-5">
              <h3 className="text-base text-[var(--color-fg)]" style={SERIF}>
                Add a source
              </h3>
              <div className="mt-3 flex flex-wrap gap-2">
                {catalog.map((entry) => (
                  <button
                    key={entry.type_id}
                    type="button"
                    onClick={() => selectType(entry.type_id)}
                    className={`rounded-full border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition ${
                      selectedType === entry.type_id
                        ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                        : "border-[var(--color-border)] text-[var(--color-fg-dim)] hover:border-[var(--color-fg-muted)]"
                    }`}
                  >
                    {humanize(entry.type_id)}
                  </button>
                ))}
              </div>

              {activeEntry && (
                <form onSubmit={handleConnect} className="mt-4 space-y-3">
                  <div>
                    <span className={fieldLabelClass}>Label</span>
                    <input
                      value={label}
                      onChange={(e) => setLabel(e.target.value)}
                      placeholder="A name for this connection"
                      className={inputClass}
                    />
                  </div>

                  {activeEntry.requires_credentials && (
                    <div>
                      <span className={fieldLabelClass}>API key</span>
                      <input
                        type="password"
                        value={credentials}
                        onChange={(e) => setCredentials(e.target.value)}
                        placeholder={`${humanize(activeEntry.type_id)} API key`}
                        className={inputClass}
                      />
                    </div>
                  )}

                  {activeEntry.config_fields.map((f) => (
                    <div key={f.name}>
                      <span className={fieldLabelClass}>
                        {f.label}
                        {f.required ? " *" : ""}
                      </span>
                      <input
                        type={f.kind === "password" ? "password" : "text"}
                        value={configValues[f.name] ?? ""}
                        onChange={(e) =>
                          setConfigValues((cur) => ({ ...cur, [f.name]: e.target.value }))
                        }
                        placeholder={f.label}
                        className={inputClass}
                      />
                    </div>
                  ))}

                  {activeEntry.capabilities.length > 0 && (
                    <div>
                      <span className={fieldLabelClass}>Serves</span>
                      <div className="flex flex-wrap gap-1.5">
                        {activeEntry.capabilities.map((cap) => (
                          <button
                            key={cap}
                            type="button"
                            onClick={() => toggleServe(cap)}
                            className={`rounded-full border px-2.5 py-1 font-mono text-[9px] uppercase tracking-wider transition ${
                              serves.includes(cap)
                                ? "border-[var(--color-accent)] bg-[var(--color-accent-soft)] text-[var(--color-fg)]"
                                : "border-[var(--color-border)] text-[var(--color-fg-muted)] hover:border-[var(--color-fg-muted)]"
                            }`}
                          >
                            {cap}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {addError && <p className="text-[12px] text-[var(--color-negative)]">{addError}</p>}

                  <button
                    type="submit"
                    disabled={submitting || !label.trim() || !!missingRequiredConfig}
                    className={primaryBtnClass}
                  >
                    {submitting ? "Connecting…" : "Connect"}
                  </button>
                </form>
              )}
            </div>
          ) : (
            <p className="mt-6 border-t border-[var(--color-border)] pt-4 font-mono text-[10px] uppercase tracking-wider text-[var(--color-fg-muted)]">
              Read-only — ask an admin to manage connected sources.
            </p>
          )}
        </>
      )}
    </div>
  );
}
