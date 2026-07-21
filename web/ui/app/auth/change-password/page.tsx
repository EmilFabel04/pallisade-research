"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card, Field, Input, toast } from "../../_ui";

export default function ChangePasswordPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (next.length < 12) {
      toast.error("New password must be at least 12 characters.");
      return;
    }
    if (next !== confirm) {
      toast.error("Passwords do not match.");
      return;
    }
    try {
      await api("/api/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: current,
          new_password: next,
        }),
      });
      await refresh();
      toast.success("Password changed successfully");
      router.replace("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Current password incorrect.");
      } else {
        toast.error("Failed to change password.");
      }
    }
  }

  return (
    <main>
      <Card className="mx-auto mt-24 max-w-sm">
        <h1 className="mb-6 font-mono text-sm uppercase tracking-widest">
          Change password
        </h1>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Current password">
            <Input
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
              autoComplete="current-password"
            />
          </Field>
          <Field label="New password (≥ 12 chars)">
            <Input
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
              minLength={12}
              autoComplete="new-password"
            />
          </Field>
          <Field label="Confirm new password">
            <Input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              autoComplete="new-password"
            />
          </Field>
          <Button type="submit" variant="primary" className="w-full">
            Save
          </Button>
        </form>
      </Card>
    </main>
  );
}
