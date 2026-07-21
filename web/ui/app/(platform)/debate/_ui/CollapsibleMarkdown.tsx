"use client";

import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Collapsible } from "@/app/_ui/Collapsible";
import { extractTakeaway, summarize } from "@/lib/debate";

export function CollapsibleMarkdown({
  body,
  label = null,
  chip,
  timestamp,
  defaultOpen = false,
  open,
  onOpenChange,
}: {
  body: string;
  label?: ReactNode;
  chip?: ReactNode;
  timestamp?: string;
  defaultOpen?: boolean;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}) {
  return (
    <Collapsible
      label={label}
      summary={extractTakeaway(body) ?? summarize(body)}
      chip={chip}
      timestamp={timestamp}
      defaultOpen={defaultOpen}
      open={open}
      onOpenChange={onOpenChange}
    >
      <article className="prose-research max-w-none text-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{body}</ReactMarkdown>
      </article>
    </Collapsible>
  );
}
