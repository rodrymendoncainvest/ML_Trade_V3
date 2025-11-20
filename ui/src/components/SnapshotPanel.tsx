import React from "react";
import type { Timeframe } from "../api";
import RsiMini from "./RsiMini";

type SnapshotStatus = "idle" | "loading" | "ready" | "error";

interface SnapshotState {
  status: SnapshotStatus;
  prob_up: number | null;
  signal: string | null;
  last_close: number | null;
  strategy: string | null;
  detail: string | null;

  // RSI
  rsi: number | null;
  lower: number | null;
  upper: number | null;

  // RSI + EMA Combo
  rsi_side: string | null;
  ema_side: string | null;

  // EMA
  ema_fast: number | null;
  ema_slow: number | null;

  // MACD
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
}

interface SnapshotPanelProps {
  symbol: string;
  tf: Timeframe;
  snapshot: SnapshotState;
  onSnapshot: () => void | Promise<void>;
  onTrain: () => void | Promise<void>;
}

/* -------------------------------------------------------
   Barra RSI (a que já usavas)
------------------------------------------------------- */
function RsiBar({ rsi, lower, upper }: { rsi: number; lower: number; upper: number }) {
  const pos = Math.min(100, Math.max(0, rsi));

  return (
    <div style={{ marginTop: "12px", width: "100%" }}>
      <div className="snap-rsi-label">
        RSI: {rsi.toFixed(1)} &nbsp; | &nbsp; {lower} / {upper}
      </div>

      <div className="snap-rsi-bar">
        <div className="snap-rsi-zone snap-rsi-low" />
        <div className="snap-rsi-zone snap-rsi-mid" />
        <div className="snap-rsi-zone snap-rsi-high" />

        <div className="snap-rsi-pointer" style={{ left: `${pos}%` }} />
      </div>
    </div>
  );
}

/* -------------------------------------------------------
   Interpretação MACD (UI only)
------------------------------------------------------- */
function interpretMacd(macd: number, signal: number, hist: number): string {
  const diff = Math.abs(hist);

  if (macd > signal) return "Tendência a subir (buy)";
  if (macd < signal) return "Tendência a cair (sell)";
  if (diff < 0.1) return "Momentum neutro";

  return "Indefinido";
}

/* -------------------------------------------------------
   Componente Principal
------------------------------------------------------- */
export default function SnapshotPanel({
  symbol,
  tf,
  snapshot,
  onSnapshot,
  onTrain,
}: SnapshotPanelProps) {
  const {
    status,
    prob_up,
    signal,
    last_close,
    strategy,
    detail,

    rsi,
    lower,
    upper,

    rsi_side,
    ema_side,

    ema_fast,
    ema_slow,

    macd,
    macd_signal,
    macd_hist,
  } = snapshot;

  const busy = status === "loading";

  return (
    <div className="snap-card">
      <div className="snap-header">
        <div>
          <div className="snap-title">Snapshot ML</div>
          <div className="snap-sub">{symbol} · {tf}</div>
        </div>
      </div>

      <div className="snap-body">

        <div className="snap-row">
          <span className="snap-label">Sinal final:</span>
          <span className="snap-value">{signal ?? "-"}</span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Prob. Up:</span>
          <span className="snap-value">
            {prob_up !== null ? (prob_up * 100).toFixed(1) + "%" : "-"}
          </span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Last close:</span>
          <span className="snap-value">
            {last_close !== null ? last_close.toFixed(2) : "-"}
          </span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Estratégia:</span>
          <span className="snap-value">{strategy ?? "-"}</span>
        </div>

        {detail && (
          <div className="snap-row">
            <span className="snap-label">Detalhes:</span>
            <span className="snap-value">{detail}</span>
          </div>
        )}

        {/* RSI BAR + Mini RSI */}
        {rsi !== null && lower !== null && upper !== null && (
          <>
            <RsiBar rsi={rsi} lower={lower} upper={upper} />
            <RsiMini rsi={rsi} />
          </>
        )}

        {/* RSI + EMA Combo extra labels */}
        {strategy === "rsi_ema_combo" && (
          <>
            <div className="snap-row" style={{ marginTop: "8px" }}>
              <span className="snap-label">RSI Side:</span>
              <span className="snap-value">{rsi_side ?? "-"}</span>
            </div>

            <div className="snap-row">
              <span className="snap-label">EMA Side:</span>
              <span className="snap-value">{ema_side ?? "-"}</span>
            </div>
          </>
        )}

        {/* MACD BLOCK */}
        {strategy === "macd_cross" &&
          macd !== null &&
          macd_signal !== null &&
          macd_hist !== null && (
            <>
              <div className="snap-row" style={{ marginTop: "10px" }}>
                <span className="snap-label">MACD:</span>
                <span className="snap-value">{macd.toFixed(2)}</span>
              </div>

              <div className="snap-row">
                <span className="snap-label">Signal:</span>
                <span className="snap-value">{macd_signal.toFixed(2)}</span>
              </div>

              <div className="snap-row">
                <span className="snap-label">Histograma:</span>
                <span className="snap-value">{macd_hist.toFixed(2)}</span>
              </div>

              <div className="snap-row">
                <span className="snap-label">Interpretação:</span>
                <span className="snap-value">
                  {interpretMacd(macd, macd_signal, macd_hist)}
                </span>
              </div>
            </>
          )}

      </div>

      <div className="snap-actions">
        <button className="snap-btn primary" onClick={onSnapshot} disabled={busy}>
          Atualizar
        </button>

        <button className="snap-btn" onClick={onTrain} disabled={busy}>
          Reentreinar
        </button>
      </div>

      {status === "loading" && (
        <div className="snap-status">A atualizar…</div>
      )}
      {status === "error" && (
        <div className="snap-status snap-error">Erro ao obter sinal.</div>
      )}
    </div>
  );
}