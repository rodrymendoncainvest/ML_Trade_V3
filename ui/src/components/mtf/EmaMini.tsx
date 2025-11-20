// ui/src/components/mtf/EmaMini.tsx
import React from "react";

interface Props {
  side: "buy" | "sell" | "hold" | string | undefined;
}

export default function EmaMini({ side }: Props) {
  const color =
    side === "buy" ? "#2ecc71" :
    side === "sell" ? "#e74c3c" :
    "#999";

  return (
    <div
      className="mtf-mini-ema"
      style={{ backgroundColor: color }}
    />
  );
}
