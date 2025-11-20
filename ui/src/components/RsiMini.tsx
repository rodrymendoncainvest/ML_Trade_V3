import React from "react";
import "./RsiMini.css";

export default function RsiMini({ rsi }: { rsi: number }) {
  const pos = Math.min(100, Math.max(0, rsi));

  return (
    <div className="rsi-mini">
      <div className="rsi-mini-bar">
        <div
          className="rsi-mini-fill"
          style={{ width: `${pos}%` }}
        />
      </div>

      <div className="rsi-mini-value">
        {rsi.toFixed(1)}
      </div>
    </div>
  );
}
