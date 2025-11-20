// ui/src/components/mtf/MacdMini.tsx
import React from "react";

interface Props {
  hist: number;
}

export default function MacdMini({ hist }: Props) {
  const color = hist >= 0 ? "#2ecc71" : "#e74c3c";
  const size = Math.min(20, Math.abs(hist) * 40);

  return (
    <div
      className="mtf-mini-macd-bar"
      style={{
        height: `${size}px`,
        backgroundColor: color,
      }}
    />
  );
}
