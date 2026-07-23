"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, MicOff } from "lucide-react";
import { IconButton } from "./IconButton";

// Minimal Web Speech API typing (not in standard lib.dom).
interface SpeechRecognitionAlt { transcript: string }
interface SpeechRecognitionResultLike { 0: SpeechRecognitionAlt; isFinal: boolean }
interface SpeechRecognitionEventLike {
  resultIndex: number;
  results: { length: number; [i: number]: SpeechRecognitionResultLike };
}
interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((e: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

function getCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export function MicButton({
  onTranscript,
  lang = "en-US",
  size = "sm",
  className = "",
}: {
  onTranscript: (text: string) => void;
  lang?: string;
  size?: "sm" | "md";
  className?: string;
}) {
  const [supported, setSupported] = useState(false);
  const [recording, setRecording] = useState(false);
  const recRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    setSupported(getCtor() !== null);
    return () => recRef.current?.stop();
  }, []);

  if (!supported) return null;

  function toggle() {
    if (recording) {
      recRef.current?.stop();
      return;
    }
    const Ctor = getCtor();
    if (!Ctor) return;
    const rec = new Ctor();
    rec.lang = lang;
    rec.continuous = false;
    rec.interimResults = true;
    rec.onresult = (e) => {
      let finalText = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) finalText += r[0].transcript;
      }
      if (finalText) onTranscript(finalText);
    };
    rec.onerror = () => setRecording(false);
    rec.onend = () => setRecording(false);
    recRef.current = rec;
    rec.start();
    setRecording(true);
  }

  return (
    <IconButton
      icon={recording ? MicOff : Mic}
      label={recording ? "Stop dictation" : "Dictate"}
      onClick={toggle}
      size={size}
      variant={recording ? "accent" : "ghost"}
      className={`${recording ? "pulse-dot" : ""} ${className}`}
      type="button"
    />
  );
}
