import { api } from "@/lib/api";

export interface ConfigField {
  name: string;
  label: string;
  kind: string;
  required: boolean;
}

export interface CatalogEntry {
  type_id: string;
  requires_credentials: boolean;
  config_fields: ConfigField[];
  capabilities: string[];
}

export interface Connection {
  id: string;
  connector_type: string;
  label: string;
  status: "disconnected" | "connected" | "error";
  credentials_set: boolean;
  config: Record<string, unknown>;
  serves: string[];
  last_error: string | null;
}

export interface TestResult {
  status: "connected" | "error";
  result: { ok: boolean; kind: string; detail: string };
}

export const getCatalog = () => api<CatalogEntry[]>("/api/connections/catalog");

export const listConnections = () => api<Connection[]>("/api/connections");

export const createConnection = (body: {
  connector_type: string;
  label: string;
  credentials?: string;
  config?: Record<string, unknown>;
  serves?: string[];
}) =>
  api<Connection>("/api/connections", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const testConnection = (id: string) =>
  api<TestResult>(`/api/connections/${id}/test`, { method: "POST" });

export const deleteConnection = (id: string) =>
  api<void>(`/api/connections/${id}`, { method: "DELETE" });
