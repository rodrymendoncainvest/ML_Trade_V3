// -------------------------------------------------------------
// API BASE
// -------------------------------------------------------------
export const API_BASE = "http://localhost:8001";

// -------------------------------------------------------------
// Tipos base
// -------------------------------------------------------------
export type Timeframe = "1d" | "1h" | "30m" | "15m" | "5m";

export interface SignalPayload {
  proba_up: number | null;
  signal: string;
  last_close: number | null;
  detail?: string;
}

export interface SignalMeta {
  tf: string;
  strategy: string;
  provider?: string;

  rsi?: number;
  thresholds?: {
    lower: number;
    upper: number;
  };

  values?: {
    ema_fast: number;
    ema_slow: number;
  };

  rsi_side?: string;
  ema_side?: string;

  macd?: {
    macd: number;
    signal: number;
    hist: number;
  };
}

export interface SignalApiResponse {
  ok: boolean;
  signal: SignalPayload;
  meta: SignalMeta;
}

// -------------------------------------------------------------
// /signals/check
// -------------------------------------------------------------
export async function fetchSignal(
  symbol: string,
  tf: Timeframe,
  strategy:
    | "rsi_cross"
    | "ema_cross"
    | "rsi_ema_combo"
    | "macd_cross" = "rsi_cross"
): Promise<SignalApiResponse | null> {
  const params = new URLSearchParams({ symbol, tf, strategy });
  const url = `${API_BASE}/signals/check?${params.toString()}`;

  try {
    const res = await fetch(url);
    if (!res.ok) return null;

    const txt = await res.text();
    if (txt.startsWith("<")) return null;

    const raw = JSON.parse(txt);

    let proba_up = 0.5;
    if (raw.signal === "buy") proba_up = 0.7;
    if (raw.signal === "sell") proba_up = 0.3;

    let detail: string | undefined;

    if (raw.values) {
      detail = `EMA fast=${raw.values.ema_fast.toFixed(
        2
      )}, slow=${raw.values.ema_slow.toFixed(2)}`;
    }

    if (raw.macd) {
      detail = `MACD=${raw.macd.macd.toFixed(2)}, Sig=${raw.macd.signal.toFixed(
        2
      )}, Hist=${raw.macd.hist.toFixed(2)}`;
    }

    return {
      ok: true,
      signal: {
        signal: raw.signal,
        proba_up,
        last_close:
          typeof raw.last_close === "number" ? raw.last_close : null,
        detail,
      },
      meta: {
        tf: raw.tf,
        strategy: raw.strategy,
        provider: raw.provider,
        rsi: raw.rsi,
        thresholds: raw.thresholds,
        values: raw.values,
        rsi_side: raw.rsi_side,
        ema_side: raw.ema_side,
        macd: raw.macd,
      },
    };
  } catch {
    return null;
  }
}

// -------------------------------------------------------------
// MTF
// -------------------------------------------------------------
export interface MtfFrame {
  rsi: number;
  ema: string;
  macd: {
    macd: number;
    signal: number;
    hist: number;
  };
  final: string;
}

export interface MtfResponse {
  symbol: string;
  provider: string;
  mtf: Record<Timeframe, MtfFrame>;
}

export async function fetchMTF(symbol: string): Promise<MtfResponse | null> {
  const url = `${API_BASE}/signals/mtf?symbol=${encodeURIComponent(symbol)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) return null;

    const txt = await res.text();
    if (txt.startsWith("<")) return null;

    return JSON.parse(txt) as MtfResponse;
  } catch {
    return null;
  }
}

// =====================================================================
// ML_V3 REST
// =====================================================================

export async function fetchMLTrainV3(symbol: string) {
  const res = await fetch(`${API_BASE}/ml_v3/train`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchMLPredictV3(
  symbol: string,
  risk_mode = "moderate"
) {
  const url = `${API_BASE}/ml_v3/predict?symbol=${encodeURIComponent(
    symbol
  )}&risk_mode=${risk_mode}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchMLBacktestV3(
  symbol: string,
  risk_mode = "moderate"
) {
  const url = `${API_BASE}/ml_v3/backtest?symbol=${encodeURIComponent(
    symbol
  )}&risk_mode=${risk_mode}`;
  const res = await fetch(url);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchMLReportV3(symbol: string) {
  const res = await fetch(`${API_BASE}/ml_v3/report`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol }),
  });
  if (!res.ok) return null;
  return res.json();
}

// =====================================================================
// ML SNAPSHOT (NOVO!!!)
// =====================================================================

export async function fetchMLSnapshotV3(symbol: string) {
  const url = `${API_BASE}/ml_v3/snapshot?symbol=${encodeURIComponent(symbol)}`;

  const res = await fetch(url);
  if (!res.ok) return null;

  return res.json();
}

// =====================================================================
// SSE — FULL RUN PIPELINE
// =====================================================================

export function streamMLFullRunV3(
  symbol: string,
  onEvent: (ev: { progress?: number; message?: string }) => void,
  onDone: (final: any) => void,
  onError: (err: any) => void
) {
  const url = `${API_BASE}/ml_v3/full_run_sse?symbol=${encodeURIComponent(
    symbol
  )}`;

  const es = new EventSource(url);

  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);

      if (data.error) {
        onError(data.error);
        es.close();
        return;
      }

      if (data.done) {
        onDone(data);
        es.close();
        return;
      }

      onEvent(data);
    } catch (err) {
      console.error("Erro SSE:", err);
    }
  };

  es.onerror = (err) => {
    onError(err);
    es.close();
  };

  return es;
}
