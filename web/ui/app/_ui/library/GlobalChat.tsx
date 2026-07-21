"use client";
import { useMemo } from "react";
import { ChatPanel } from "../ChatPanel";
import { globalChatSource } from "@/lib/chat";

const SUGGESTIONS = [
  'Summarise the strongest memo in the library.',
  'Compare @"final decision" memos for the same ticker over time.',
  'What is the highest-conviction BUY in the library right now?',
  'Which memos cite the weakest evidence?',
];

export function GlobalChat() {
  const source = useMemo(() => globalChatSource(), []);
  return (
    <ChatPanel
      source={source}
      suggestions={SUGGESTIONS}
      placeholder={'Ask across all memos. Use @"Title" to reference a specific one.'}
      statusLine={
        <span>
          Tip: type <code className="font-mono">@&quot;memo title&quot;</code> to scope the
          answer to that memo.
        </span>
      }
    />
  );
}
