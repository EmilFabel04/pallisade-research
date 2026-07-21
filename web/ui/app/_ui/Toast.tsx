"use client";

import { Toaster as SonnerToaster, toast } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      theme="dark"
      position="bottom-right"
      richColors={false}
      toastOptions={{
        style: {
          background: "var(--color-surface-2)",
          color: "var(--color-fg)",
          border: "1px solid var(--color-border)",
          fontFamily:
            "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
          fontSize: "13px",
        },
      }}
    />
  );
}

export { toast };
