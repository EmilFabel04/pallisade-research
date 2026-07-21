"use client";

import { useCallback, useEffect, useState } from "react";

export type ArtefactKind = "research" | "debate" | "clip";

export interface Artefact {
  id: string;
  kind: ArtefactKind;
  title: string;
  createdAt: string; // ISO
  starred: boolean;
  sourceCount: number;
  payload: unknown; // CitedAnswer | DebateTranscript | string, by kind
}

const KEY = "pallisade.artefacts.v1";

function read(): Artefact[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Artefact[]) : [];
  } catch {
    return [];
  }
}

function write(items: Artefact[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEY, JSON.stringify(items));
  window.dispatchEvent(new Event("artefacts:changed"));
}

export function saveArtefact(
  input: Omit<Artefact, "id" | "createdAt" | "starred">,
): Artefact {
  const record: Artefact = {
    ...input,
    id: `af_${Math.random().toString(36).slice(2, 10)}`,
    createdAt: new Date().toISOString(),
    starred: false,
  };
  write([record, ...read()]);
  return record;
}

export function useArtefacts() {
  const [items, setItems] = useState<Artefact[]>([]);
  const refresh = useCallback(() => setItems(read()), []);

  useEffect(() => {
    refresh();
    const onChange = () => refresh();
    window.addEventListener("artefacts:changed", onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener("artefacts:changed", onChange);
      window.removeEventListener("storage", onChange);
    };
  }, [refresh]);

  const toggleStar = useCallback((id: string) => {
    write(read().map((a) => (a.id === id ? { ...a, starred: !a.starred } : a)));
  }, []);

  const remove = useCallback((id: string) => {
    write(read().filter((a) => a.id !== id));
  }, []);

  return { items, toggleStar, remove, refresh };
}

// Idempotently seed first-run demo data. Safe to call on mount. Uses write()
// so the artefacts:changed event fires on first seed — any already-mounted
// useArtefacts consumer (e.g. the Dashboard) refreshes immediately rather than
// waiting for a reload. The localStorage guard means this only fires once.
export function ensureSeeded(seed: Artefact[]) {
  if (typeof window === "undefined") return;
  if (window.localStorage.getItem(KEY) !== null) return;
  write(seed);
}
