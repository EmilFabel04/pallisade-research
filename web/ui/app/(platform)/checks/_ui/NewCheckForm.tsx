"use client";

import { useState, type FormEvent } from "react";

import { Button, Card, toast } from "@/app/_ui";
import { createMemoCheck, type MemoCheck } from "@/lib/memoChecks";

export function NewCheckForm({
  onCreated,
}: {
  onCreated: (check: MemoCheck) => void;
}) {
  const [memoText, setMemoText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const disabled = submitting || memoText.trim().length === 0;

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    setSubmitting(true);
    try {
      const check = await createMemoCheck({ memo_text: memoText });
      onCreated(check);
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <form onSubmit={onSubmit}>
        <label
          htmlFor="memo-text"
          className="mb-1.5 block font-mono text-[11px] uppercase tracking-wider text-[var(--color-fg-muted)]"
        >
          Memo text
        </label>
        <textarea
          id="memo-text"
          value={memoText}
          onChange={(e) => setMemoText(e.target.value)}
          placeholder="Paste the IC memo text here…"
          className="min-h-[10rem] w-full resize-y rounded-md border border-[var(--color-border)] bg-transparent p-3 text-sm text-[var(--color-fg)] placeholder:text-[var(--color-fg-muted)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <div className="mt-3 flex items-center justify-between gap-4">
          <p className="text-[11px] text-[var(--color-fg-muted)]">
            Checks against your whole document corpus.
          </p>
          <Button type="submit" disabled={disabled}>
            {submitting ? "Running…" : "Run check"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
