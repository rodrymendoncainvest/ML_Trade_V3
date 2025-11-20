// ui/src/App.tsx
import { useState, useEffect } from "react";
import "./App.css";

import PriceChart from "./components/PriceChart";
import WatchlistPanel from "./components/WatchlistPanel";
import SnapshotPanel from "./components/SnapshotPanel";
import NewsPanel from "./components/NewsPanel";
import MtfPanel from "./components/MtfPanel";

import {
  fetchSignal,
  fetchTrain,
  fetchMTF,
  type Timeframe,
} from "./api";

// -------------------------------
// Tipos locais
// -------------------------------
type SnapshotStatus = "idle" | "loading" | "ready" | "error";

type StrategyKey =
  | "rsi_cross"
  | "ema_cross"
  | "rsi_ema_combo"
  | "macd_cross";

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

  // Combo
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

// -------------------------------
// Componente principal
// -------------------------------
export default function App() {
  const [symbol, setSymbol] = useState("ASML.AS");
  const [tf, setTf] = useState<Timeframe>("1h");
  const [limit, setLimit] = useState(500);
  const [strategy, setStrategy] = useState<StrategyKey>("rsi_cross");

  const [snapshot, setSnapshot] = useState<SnapshotState>({
    status: "idle",
    prob_up: null,
    signal: null,
    last_close: null,
    strategy: null,
    detail: null,

    rsi: null,
    lower: null,
    upper: null,

    rsi_side: null,
    ema_side: null,

    ema_fast: null,
    ema_slow: null,

    macd: null,
    macd_signal: null,
    macd_hist: null,
  });

  const [mtf, setMtf] = useState<any>(null);
  const [mtfStatus, setMtfStatus] =
    useState<"idle" | "loading" | "ready" | "error">("idle");

  // ---------------------------------------------------------
  // HANDLE SNAPSHOT ML
  // ---------------------------------------------------------
  async function handleSnapshot() {
    setSnapshot({
      status: "loading",
      prob_up: null,
      signal: null,
      last_close: null,
      strategy: null,
      detail: null,

      rsi: null,
      lower: null,
      upper: null,

      rsi_side: null,
      ema_side: null,

      ema_fast: null,
      ema_slow: null,

      macd: null,
      macd_signal: null,
      macd_hist: null,
    });

    const res = await fetchSignal(symbol, tf, strategy);
    if (!res) {
      setSnapshot((s) => ({ ...s, status: "error" }));
      return;
    }

    setSnapshot({
      status: "ready",
      prob_up: res.signal.proba_up,
      signal: res.signal.signal,
      last_close: res.signal.last_close,
      strategy: res.meta.strategy,
      detail: res.signal.detail ?? null,

      rsi: res.meta.rsi ?? null,
      lower: res.meta.thresholds?.lower ?? null,
      upper: res.meta.thresholds?.upper ?? null,

      rsi_side: res.meta.rsi_side ?? null,
      ema_side: res.meta.ema_side ?? null,

      ema_fast: res.meta.values?.ema_fast ?? null,
      ema_slow: res.meta.values?.ema_slow ?? null,

      macd: res.meta.macd?.macd ?? null,
      macd_signal: res.meta.macd?.signal ?? null,
      macd_hist: res.meta.macd?.hist ?? null,
    });
  }

  // ---------------------------------------------------------
  // HANDLE MTF (executado sempre que muda o símbolo)
  // ---------------------------------------------------------
  async function refreshMTF() {
    setMtfStatus("loading");

    const res = await fetchMTF(symbol);

    if (!res) {
      setMtfStatus("error");
      setMtf(null);
      return;
    }

    setMtf(res);
    setMtfStatus("ready");
  }

  useEffect(() => {
    refreshMTF();
  }, [symbol]);

  // ---------------------------------------------------------
  // TREINO
  // ---------------------------------------------------------
  async function handleTrain() {
    const ok = await fetchTrain();
    alert(ok ? `Treino iniciado para ${symbol}` : "Treino não disponível.");
  }

  // ---------------------------------------------------------
  // RENDER
  // ---------------------------------------------------------
  return (
    <div className="app-root">
      
      <header className="topbar">
        <div className="logo">ML Trade</div>

        <div className="controls">

          <div className="ctrl-group">
            <label>Símbolo</label>
            <input value={symbol} onChange={(e) => setSymbol(e.target.value)} />
          </div>

          <div className="ctrl-group">
            <label>Timeframe</label>
            <select value={tf} onChange={(e) => setTf(e.target.value as Timeframe)}>
              <option value="1d">1d</option>
              <option value="1h">1h</option>
              <option value="30m">30m</option>
              <option value="15m">15m</option>
              <option value="5m">5m</option>
            </select>
          </div>

          <div className="ctrl-group">
            <label>Velas</label>
            <select value={limit} onChange={(e) => setLimit(Number(e.target.value))}>
              <option value={500}>500</option>
              <option value={1000}>1000</option>
              <option value={2000}>2000</option>
              <option value={5000}>5000</option>
              <option value={10000}>10000</option>
            </select>
          </div>

          <div className="ctrl-group">
            <label>Estratégia</label>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value as StrategyKey)}>
              <option value="rsi_cross">RSI Cross</option>
              <option value="ema_cross">EMA Cross</option>
              <option value="rsi_ema_combo">RSI + EMA Combo</option>
              <option value="macd_cross">MACD Cross</option>
            </select>
          </div>

        </div>
      </header>

      <div className="layout">
        
        <div className="chart-area">
          <PriceChart symbol={symbol} tf={tf} limit={limit} />
        </div>

        <aside className="sidepanel">
          
          <WatchlistPanel
            current={symbol}
            onSelect={setSymbol}
          />

          <SnapshotPanel
            symbol={symbol}
            tf={tf}
            snapshot={snapshot}
            onSnapshot={handleSnapshot}
            onTrain={handleTrain}
          />

          <MtfPanel
            loading={mtfStatus === "loading"}
            error={mtfStatus === "error"}
            final_signal={mtf?.final_signal ?? null}
            tfs={mtf?.tfs ?? null}
            onRefresh={refreshMTF}
          />

          <NewsPanel symbol={symbol} />

        </aside>
      </div>
    </div>
  );
}
