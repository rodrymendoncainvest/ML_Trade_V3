import React, { useState } from "react";
import type { Timeframe } from "../api";

import {
  streamMLFullRunV3,
  fetchMLPredictV3,
  fetchMLBacktestV3,
  fetchMLReportV3,
  fetchMLSnapshotV3
} from "../api";

import RsiMini from "./RsiMini";
import "./SnapshotPanel.css";

type SnapshotStatus = "idle" | "loading" | "ready" | "error";

interface SnapshotState {
  status: SnapshotStatus;
  prob_up: number | null;
  signal: string | null;
  last_close: number | null;
  strategy: string | null;
  detail: string | null;
  rsi: number | null;
  lower: number | null;
  upper: number | null;
  rsi_side: string | null;
  ema_side: string | null;
  ema_fast: number | null;
  ema_slow: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
}

export default function SnapshotPanel({
  symbol,
  tf,
  snapshot,
  onSnapshot,
}: {
  symbol: string;
  tf: Timeframe;
  snapshot: SnapshotState;
  onSnapshot: () => void | Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState("");
  const [finalOutput, setFinalOutput] = useState<any>(null);

  // -----------------------------------------------------------------------
  // ATUALIZAR (SNAPSHOT DO MODELO)
  // -----------------------------------------------------------------------
  async function updateSnapshot() {
    const data = await fetchMLSnapshotV3(symbol);
    setFinalOutput(data);

    if (onSnapshot) onSnapshot();
  }

  // -----------------------------------------------------------------------
  // BOTÃO TREINO — FULL PIPELINE (SSE)
  // -----------------------------------------------------------------------
  function startFullRun() {
    setBusy(true);
    setFinalOutput(null);
    setProgress(0);
    setStatusMsg("A iniciar pipeline...");

    streamMLFullRunV3(
      symbol,
      (ev) => {
        if (ev.progress !== undefined) setProgress(ev.progress);
        if (ev.message) setStatusMsg(ev.message);
      },
      (final) => {
        setBusy(false);
        setProgress(100);
        setStatusMsg("Pipeline completo.");
        setFinalOutput(final);
      },
      (err) => {
        setBusy(false);
        setStatusMsg("Erro no pipeline.");
        console.error(err);
      }
    );
  }

  // -----------------------------------------------------------------------
  // SECUNDÁRIOS
  // -----------------------------------------------------------------------
  async function mlPredict() {
    const out = await fetchMLPredictV3(symbol, "moderate");
    setFinalOutput(out);
  }

  async function mlBacktest() {
    const out = await fetchMLBacktestV3(symbol, "moderate");
    setFinalOutput(out);
  }

  async function mlReport() {
    const out = await fetchMLReportV3(symbol);
    setFinalOutput(out);
  }

  // -----------------------------------------------------------------------
  return (
    <div className="snap-card">
      <div className="snap-header">
        <div>
          <div className="snap-title">Snapshot ML</div>
          <div className="snap-sub">{symbol} · {tf}</div>
        </div>

        <button className="snap-btn" onClick={updateSnapshot}>
          Atualizar
        </button>
      </div>

      <div className="snap-body">
        <div className="snap-row">
          <span className="snap-label">Sinal final:</span>
          <span className="snap-value">{snapshot.signal ?? "-"}</span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Prob. Up:</span>
          <span className="snap-value">
            {snapshot.prob_up !== null ? (snapshot.prob_up * 100).toFixed(1) + "%" : "-"}
          </span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Last close:</span>
          <span className="snap-value">
            {snapshot.last_close !== null ? snapshot.last_close.toFixed(2) : "-"}
          </span>
        </div>

        <div className="snap-row">
          <span className="snap-label">Estratégia:</span>
          <span className="snap-value">{snapshot.strategy ?? "-"}</span>
        </div>

        {snapshot.detail && (
          <div className="snap-row">
            <span className="snap-label">Detalhes:</span>
            <span className="snap-value">{snapshot.detail}</span>
          </div>
        )}

        {snapshot.rsi !== null &&
          snapshot.lower !== null &&
          snapshot.upper !== null && (
            <>
              <div style={{ marginTop: "12px" }} />
              <RsiMini rsi={snapshot.rsi} />
            </>
          )}
      </div>

      <div className="snap-actions" style={{ marginTop: "12px" }}>
        <button
          className="snap-btn primary"
          onClick={startFullRun}
          disabled={busy}
          style={{ width: "100%", padding: "8px 0", fontSize: "14px" }}
        >
          TREINO
        </button>
      </div>

      {busy && (
        <>
          <div className="sse-bar">
            <div className="sse-bar-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="snap-status">{statusMsg}</div>
        </>
      )}

      <div className="snap-actions" style={{ marginTop: "12px" }}>
        <button className="snap-btn" onClick={mlPredict}>Sinal</button>
        <button className="snap-btn" onClick={mlBacktest}>Backtest</button>
        <button className="snap-btn" onClick={mlReport}>Report</button>
      </div>

      {finalOutput && (
        <pre className="snap-ml-output">
          {JSON.stringify(finalOutput, null, 2)}
        </pre>
      )}
    </div>
  );
}
