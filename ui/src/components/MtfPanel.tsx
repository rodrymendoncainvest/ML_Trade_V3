// ui/src/components/MtfPanel.tsx
import React from "react";
import "./MtfPanel.css";

interface MtfEntry {
  signal_rsi?: string;
  rsi?: number;

  signal_ema?: string;
  ema_fast?: number;
  ema_slow?: number;

  signal_macd?: string;
  macd?: {
    macd: number;
    signal: number;
    hist: number;
  };
}

interface Props {
  loading: boolean;
  error: boolean;
  final_signal: string | null;
  tfs: Record<string, MtfEntry> | null;
  onRefresh: () => void;
}

export default function MtfPanel({
  loading,
  error,
  final_signal,
  tfs,
  onRefresh,
}: Props) {
  return (
    <div className="mtf-card">
      {/* HEADER */}
      <div className="mtf-header">
        <div className="mtf-title">Multi-Timeframe (MTF)</div>
        <button
          className="mtf-refresh"
          disabled={loading}
          onClick={onRefresh}
        >
          Atualizar
        </button>
      </div>

      {/* LOADING / ERRO */}
      {loading && <div className="mtf-loading">A carregar…</div>}
      {error && <div className="mtf-error">Erro ao obter dados.</div>}

      {/* CONTEÚDO */}
      {!loading && !error && tfs && (
        <div className="mtf-body">
          {/* SINAL FINAL */}
          <div className="mtf-final">
            <span className="mtf-final-label">Sinal final:</span>
            <span className="mtf-final-value">{final_signal ?? "-"}</span>
          </div>

          {/* TIMEFRAMES: 1D / 1H / 30M */}
          {["1d", "1h", "30m"].map((tf) => {
            const frame = tfs[tf];

            return (
              <div key={tf} className="mtf-block">
                <div className="mtf-tf-title">{tf.toUpperCase()}</div>

                {/* RSI */}
                <div className="mtf-row">
                  <span className="mtf-label">RSI:</span>
                  <span className="mtf-value">
                    {frame?.rsi !== undefined
                      ? `${frame.rsi.toFixed(1)} (${frame.signal_rsi ?? "-"})`
                      : "-"}
                  </span>
                </div>

                {/* Barra visual RSI */}
                <div
                  className={`mtf-bar mtf-bar--${frame?.signal_rsi ?? "hold"}`}
                ></div>

                {/* EMA */}
                <div className="mtf-row">
                  <span className="mtf-label">EMA:</span>
                  <span className="mtf-value">
                    {frame?.ema_fast !== undefined &&
                    frame?.ema_slow !== undefined
                      ? `${frame.ema_fast.toFixed(2)} / ${frame.ema_slow.toFixed(
                          2
                        )} (${frame.signal_ema ?? "-"})`
                      : "-"}
                  </span>
                </div>

                {/* Barra visual EMA */}
                <div
                  className={`mtf-bar mtf-bar--${frame?.signal_ema ?? "hold"}`}
                ></div>

                {/* MACD */}
                <div className="mtf-row">
                  <span className="mtf-label">MACD:</span>
                  <span className="mtf-value">
                    {frame?.macd
                      ? `${frame.macd.macd.toFixed(
                          2
                        )} / ${frame.macd.signal.toFixed(2)} (${
                          frame.signal_macd ?? "-"
                        })`
                      : "-"}
                  </span>
                </div>

                {/* Barra visual MACD */}
                <div
                  className={`mtf-bar mtf-bar--${frame?.signal_macd ?? "hold"}`}
                ></div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
