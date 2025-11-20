// ui/src/api.ts
// -------------------------------------------------------------
// Config base da API
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

  // RSI
  rsi?: number;
  thresholds?: {
    lower: number;
    upper: number;
  };

  // EMA
  values?: {
    ema_fast: number;
    ema_slow: number;
  };

  // COMBO
  rsi_side?: string;
  ema_side?: string;

  // MACD
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
// /signals/check → Snapshot ML (RSI, EMA, COMBO, MACD)
// -------------------------------------------------------------
export async function fetchSignal(
  symbol: string,
  tf: Timeframe,
  strategy: "rsi_cross" | "ema_cross" | "rsi_ema_combo" | "macd_cross" = "rsi_cross"
): Promise<SignalApiResponse | null> {
  const params = new URLSearchParams({ symbol, tf, strategy });
  const url = `${API_BASE}/signals/check?${params.toString()}`;

  try {
    const res = await fetch(url);
    if (!res.ok) return null;

    const txt = await res.text();
    if (txt.startsWith("<")) return null;

    const raw = JSON.parse(txt);

    // probabilidade "fake" (temporário)
    let proba_up = 0.5;
    if (raw.signal === "buy") proba_up = 0.7;
    if (raw.signal === "sell") proba_up = 0.3;

    // detalhe dinamicamente
    let detail: string | undefined = undefined;

    if (raw.values) {
      detail = `EMA fast=${raw.values.ema_fast.toFixed(2)}, slow=${raw.values.ema_slow.toFixed(2)}`;
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
        last_close: typeof raw.last_close === "number" ? raw.last_close : null,
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
// Treino (stub)
// -------------------------------------------------------------
export async function fetchTrain(): Promise<boolean> {
  return false;
}

// -------------------------------------------------------------
// MTF – /signals/mtf
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
