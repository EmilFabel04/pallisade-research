"use client";

export function Emblem({
  size = 24,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  const dim = `${size}px`;
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/pallisade_emblem.svg"
      alt=""
      aria-hidden
      width={size}
      height={size}
      className={className}
      style={{ display: "block", width: dim, height: dim }}
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).style.display = "none";
      }}
    />
  );
}
