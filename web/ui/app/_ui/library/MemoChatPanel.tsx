"use client";
import { useMemo } from "react";
import { ChatPanel } from "../ChatPanel";
import { libraryDocChatSource } from "@/lib/chat";

const SUGGESTIONS = [
  "Summarise the thesis in three bullets.",
  "What is the bear case?",
  "Which numbers in this memo are weakest?",
  "What evidence supports the recommendation?",
];

export function MemoChatPanel({ docId }: { docId: string }) {
  const source = useMemo(() => libraryDocChatSource(docId), [docId]);
  return (
    <ChatPanel
      source={source}
      suggestions={SUGGESTIONS}
      placeholder="Ask about this memo…"
    />
  );
}
