// ui/src/components/mtf/RsiMini.tsx
import React from "react";

interface Props {
  rsi: number;
}

export default function RsiMini({ rsi }: Props) {
  const pct = Math.min(100, Math.max(0, rsi));

  return (
    <div className="mtf-mini-rsi-bar">
      <div
        className="mtf-mini-rsi-pointer"
        style={{ left: `${pct}%` }}
      />
    </div>
  );
}
