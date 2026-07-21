"use client";

import { useEffect, useMemo, useState } from "react";

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/**
 * Progressively reveal `fullText` word-by-word for a "streaming" feel, even
 * though the text arrives all at once. Honors prefers-reduced-motion (shows the
 * full text immediately). Cleans up its timer on unmount and when fullText changes.
 */
export function useRevealedText(
  fullText: string,
  opts: { enabled?: boolean; cadenceMs?: number } = {},
): { shown: string; done: boolean } {
  const { enabled = true, cadenceMs = 18 } = opts;
  const [count, setCount] = useState(0);
  const words = useMemo(
    () => (fullText.length ? fullText.split(/(\s+)/) : []),
    [fullText],
  );

  useEffect(() => {
    if (!enabled || prefersReducedMotion() || words.length === 0) {
      setCount(words.length);
      return;
    }
    setCount(0);
    const id = setInterval(() => {
      setCount((n) => {
        if (n >= words.length) {
          clearInterval(id);
          return n;
        }
        return n + 1;
      });
    }, cadenceMs);
    return () => clearInterval(id);
    // words is derived purely from fullText; keeping fullText in deps is
    // equivalent and avoids re-running on identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fullText, enabled, cadenceMs]);

  const shown = words.slice(0, count).join("");
  const done = count >= words.length;
  return { shown, done };
}
