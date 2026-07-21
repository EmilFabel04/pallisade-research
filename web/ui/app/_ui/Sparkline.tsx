"use client";

export type SparkTone = "ok" | "err" | "neutral";

const stroke: Record<SparkTone, string> = {
  ok: "var(--tone-ok-fg)",
  err: "var(--color-accent)",
  neutral: "var(--color-fg-muted)",
};

export function Sparkline({
  data,
  width = 90,
  height = 22,
  tone = "neutral",
  className = "",
}: {
  data: number[];
  width?: number;
  height?: number;
  tone?: SparkTone;
  className?: string;
}) {
  const pad = 1;
  const innerH = Math.max(0, height - pad * 2);
  const midY = pad + innerH / 2;

  let points: string;
  if (data.length < 2) {
    points = `0,${midY} ${width},${midY}`;
  } else {
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;
    if (range === 0) {
      points = `0,${midY} ${width},${midY}`;
    } else {
      const stepX = width / (data.length - 1);
      points = data
        .map((v, i) => {
          const x = i * stepX;
          const y = pad + (innerH - ((v - min) / range) * innerH);
          return `${x},${y}`;
        })
        .join(" ");
    }
  }

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      aria-hidden
    >
      <polyline
        fill="none"
        stroke={stroke[tone]}
        strokeWidth={1.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  );
}
