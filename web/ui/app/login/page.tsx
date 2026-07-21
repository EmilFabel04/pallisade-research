"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button, Card, Emblem, Field, Input } from "../_ui";

export default function LoginPage() {
  const router = useRouter();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await refresh();
      router.replace("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid email or password.");
      } else {
        setError("Login failed.");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-mesh relative min-h-screen">
      <Card className="mx-auto mt-24 max-w-sm">
        <div className="flex flex-col items-center text-center">
          <Emblem size={40} />
          <h1 className="mt-4 text-xl font-semibold text-[var(--color-fg)]">
            Pallisade
          </h1>
          <p className="mt-1 font-mono text-xs uppercase tracking-wider text-[var(--color-fg-dim)]">
            Sign in to continue
          </p>
        </div>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <Field label="Email">
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </Field>
          <Field label="Password">
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
          </Field>
          {error && (
            <p className="text-xs font-mono text-[var(--color-accent)]">
              {error}
            </p>
          )}
          <Button
            type="submit"
            disabled={busy}
            className="w-full"
            variant="primary"
          >
            {busy ? "Signing in…" : "Sign in"}
          </Button>
        </form>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-[var(--color-fg-muted)]">
          For licensed financial services providers and qualified professional
          analysts.
        </p>
      </Card>

      <style jsx global>{`
        .login-mesh::before {
          content: "";
          position: absolute;
          inset: 0;
          background: var(--radial-accent-page);
          pointer-events: none;
          z-index: 0;
        }
        .login-mesh > * {
          position: relative;
          z-index: 1;
        }
      `}</style>
    </main>
  );
}
