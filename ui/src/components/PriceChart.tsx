// ui/src/components/PriceChart.tsx
import React, { useEffect, useRef, useState } from "react";
import {
  createChart,
  CrosshairMode,
  ColorType,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type LineData,
  type HistogramData,
} from "lightweight-charts";
import "./PriceChart.css";
import { API_BASE } from "../api";

// ------------------------------------------------------
// TYPES
// ------------------------------------------------------
interface Candle {
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PriceChartProps {
  symbol: string;
  tf: string;
  limit: number;
}

// ------------------------------------------------------
// UTILS
// ------------------------------------------------------
function normalizeTime(ts: number): number {
  return ts > 9999999999 ? Math.floor(ts / 1000) : ts;
}

function preprocess(raw: Candle[]): Candle[] {
  const sorted = raw
    .map((c) => ({ ...c, ts: normalizeTime(c.ts) }))
    .sort((a, b) => a.ts - b.ts);

  const out: Candle[] = [];
  let last: number | null = null;

  for (const d of sorted) {
    if (d.ts !== last) {
      out.push(d);
      last = d.ts;
    }
  }
  return out;
}

// EMA
function ema(vals: number[], p: number): number[] {
  const k = 2 / (p + 1);
  const out: number[] = [];
  vals.forEach((v, i) => {
    if (i === 0) out.push(v);
    else out.push(v * k + out[i - 1] * (1 - k));
  });
  return out;
}

// Bollinger
function boll(vals: number[], period = 20, mult = 2) {
  const out = [];
  for (let i = 0; i < vals.length; i++) {
    if (i < period) {
      out.push({ upper: vals[i], lower: vals[i], mid: vals[i] });
      continue;
    }
    const slice = vals.slice(i - period, i);
    const mean = slice.reduce((a, b) => a + b, 0) / slice.length;
    const variance =
      slice.reduce((a, b) => a + (b - mean) * (b - mean), 0) / slice.length;
    const std = Math.sqrt(variance);
    out.push({
      upper: mean + mult * std,
      lower: mean - mult * std,
      mid: mean,
    });
  }
  return out;
}

// RSI
function rsi(vals: number[], p = 14): number[] {
  if (vals.length <= p) return Array(vals.length).fill(50);

  const changes = vals.map((v, i) => (i === 0 ? 0 : v - vals[i - 1]));
  const gains = changes.map((v) => (v > 0 ? v : 0));
  const losses = changes.map((v) => (v < 0 ? -v : 0));

  let avgG =
    gains.slice(1, p + 1).reduce((a, b) => a + b, 0) / p;
  let avgL =
    losses.slice(1, p + 1).reduce((a, b) => a + b, 0) / p;

  const out: number[] = [];

  for (let i = p + 1; i < vals.length; i++) {
    avgG = (avgG * (p - 1) + gains[i]) / p;
    avgL = (avgL * (p - 1) + losses[i]) / p;

    if (avgL === 0) out.push(100);
    else {
      const rs = avgG / avgL;
      out.push(100 - 100 / (1 + rs));
    }
  }

  const pad = Array(vals.length - out.length).fill(50);
  return [...pad, ...out];
}

// ------------------------------------------------------
// COMPONENT
// ------------------------------------------------------
export default function PriceChart({ symbol, tf, limit }: PriceChartProps) {
  const mainRef = useRef<HTMLDivElement | null>(null);
  const rsiRef = useRef<HTMLDivElement | null>(null);
  const volRef = useRef<HTMLDivElement | null>(null);

  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState(false);

  const [showEma9, setShowEma9] = useState(true);
  const [showEma21, setShowEma21] = useState(true);
  const [showEma50, setShowEma50] = useState(true);
  const [showBB, setShowBB] = useState(true);
  const [showRSI, setShowRSI] = useState(true);
  const [showVolume, setShowVolume] = useState(true);

  // ------------------------------------------------------
  // FETCH OHLC
  // ------------------------------------------------------
  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      try {
        const params = new URLSearchParams({
          symbol,
          tf,
          limit: String(limit),
        });

        const res = await fetch(`${API_BASE}/quotes/ohlc?${params.toString()}`);
        if (!res.ok) throw new Error("Erro HTTP");

        const data = await res.json();
        if (!data || !Array.isArray(data.rows)) throw new Error("Formato inválido");

        if (active) setCandles(data.rows as Candle[]);
      } catch (err) {
        console.error("Erro ao carregar OHLC:", err);
        if (active) setCandles([]);
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [symbol, tf, limit]);

  // ------------------------------------------------------
  // CRIAR GRÁFICOS + SINCRONIZAÇÃO
  // ------------------------------------------------------
  useEffect(() => {
    if (!mainRef.current || !rsiRef.current || !volRef.current) return;
    if (candles.length === 0) return;

    const data = preprocess(candles);
    const closes = data.map((d) => d.close);

    // MAIN
    const main = createChart(mainRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0e1114" },
        textColor: "#d1d4dc",
      },
      width: mainRef.current.clientWidth,
      height: mainRef.current.clientHeight,
      crosshair: { mode: CrosshairMode.Normal },
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      timeScale: { timeVisible: true },
    });

    const candleSeries = main.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
      borderVisible: false,
    });

    candleSeries.setData(
      data.map((d) => ({
        time: d.ts,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))
    );

    // EMAs
    const ema9Vals = ema(closes, 9);
    const ema21Vals = ema(closes, 21);
    const ema50Vals = ema(closes, 50);

    const ema9Series = main.addLineSeries({
      color: "#f1c40f",
      lineWidth: 1,
      visible: showEma9,
    });
    const ema21Series = main.addLineSeries({
      color: "#2ecc71",
      lineWidth: 1,
      visible: showEma21,
    });
    const ema50Series = main.addLineSeries({
      color: "#3498db",
      lineWidth: 1,
      visible: showEma50,
    });

    ema9Series.setData(data.map((d, i) => ({ time: d.ts, value: ema9Vals[i] })));
    ema21Series.setData(data.map((d, i) => ({ time: d.ts, value: ema21Vals[i] })));
    ema50Series.setData(data.map((d, i) => ({ time: d.ts, value: ema50Vals[i] })));

    // Bollinger
    const bb = boll(closes);
    const bbUpper = main.addLineSeries({
      color: "#9b59b6",
      lineWidth: 1,
      visible: showBB,
    });
    const bbLower = main.addLineSeries({
      color: "#9b59b6",
      lineWidth: 1,
      visible: showBB,
    });
    const bbMid = main.addLineSeries({
      color: "#9b59b6",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      visible: showBB,
    });

    bbUpper.setData(data.map((d, i) => ({ time: d.ts, value: bb[i].upper })));
    bbLower.setData(data.map((d, i) => ({ time: d.ts, value: bb[i].lower })));
    bbMid.setData(data.map((d, i) => ({ time: d.ts, value: bb[i].mid })));

    main.timeScale().fitContent();

    // RSI
    const rsiChart = createChart(rsiRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0e1114" },
        textColor: "#d1d4dc",
      },
      width: rsiRef.current.clientWidth,
      height: rsiRef.current.clientHeight,
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      timeScale: { visible: false },
    });

    const rsiSeries = rsiChart.addLineSeries({
      color: "#2ecc71",
      lineWidth: 1,
      visible: showRSI,
    });

    const rsiVals = rsi(closes);
    rsiSeries.setData(data.map((d, i) => ({ time: d.ts, value: rsiVals[i] })));

    // RSI 30/70
    const rsi30 = rsiChart.addLineSeries({
      color: "#555",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
    });
    const rsi70 = rsiChart.addLineSeries({
      color: "#555",
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
    });

    rsi30.setData(data.map((d) => ({ time: d.ts, value: 30 })));
    rsi70.setData(data.map((d) => ({ time: d.ts, value: 70 })));

    // VOLUME
    const volChart = createChart(volRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0e1114" },
        textColor: "#d1d4dc",
      },
      width: volRef.current.clientWidth,
      height: volRef.current.clientHeight,
      grid: {
        vertLines: { color: "#1f2937" },
        horzLines: { color: "#1f2937" },
      },
      timeScale: { visible: false },
    });

    const volSeries = volChart.addHistogramSeries({
      priceFormat: { type: "volume" },
      visible: showVolume,
    });

    volSeries.setData(
      data.map((d) => ({
        time: d.ts,
        value: d.volume,
        color: d.close >= d.open ? "#26a69a" : "#ef5350",
      }))
    );

    // ------------------------------------------------------
    // SINCRONIZAÇÃO ENTRE OS 3 GRÁFICOS
    // ------------------------------------------------------
    const mainScale = main.timeScale();
    const rsiScale = rsiChart.timeScale();
    const volScale = volChart.timeScale();

    let syncing = false;

    function sync(from: "main" | "rsi" | "vol", range: any) {
      if (syncing) return;
      syncing = true;

      if (from !== "main") mainScale.setVisibleRange(range);
      if (from !== "rsi") rsiScale.setVisibleRange(range);
      if (from !== "vol") volScale.setVisibleRange(range);

      syncing = false;
    }

    mainScale.subscribeVisibleTimeRangeChange((range) => range && sync("main", range));
    rsiScale.subscribeVisibleTimeRangeChange((range) => range && sync("rsi", range));
    volScale.subscribeVisibleTimeRangeChange((range) => range && sync("vol", range));

    // RESIZE
    const resize = () => {
      if (!mainRef.current || !rsiRef.current || !volRef.current) return;
      main.applyOptions({ width: mainRef.current.clientWidth });
      rsiChart.applyOptions({ width: rsiRef.current.clientWidth });
      volChart.applyOptions({ width: volRef.current.clientWidth });
    };

    window.addEventListener("resize", resize);

    return () => {
      window.removeEventListener("resize", resize);
      main.remove();
      rsiChart.remove();
      volChart.remove();
    };
  }, [candles, showEma9, showEma21, showEma50, showBB, showRSI, showVolume]);

  // ------------------------------------------------------
  // RENDER
  // ------------------------------------------------------
  return (
    <div className="pc-wrapper">
      <div className="pc-topbar">
        <div className="pc-legend">
          <span className={`tag ${showEma9 ? "" : "off"}`} onClick={() => setShowEma9(!showEma9)}>● EMA 9</span>
          <span className={`tag ${showEma21 ? "" : "off"}`} onClick={() => setShowEma21(!showEma21)}>● EMA 21</span>
          <span className={`tag ${showEma50 ? "" : "off"}`} onClick={() => setShowEma50(!showEma50)}>● EMA 50</span>
          <span className={`tag ${showBB ? "" : "off"}`} onClick={() => setShowBB(!showBB)}>● Bollinger</span>
          <span className={`tag ${showRSI ? "" : "off"}`} onClick={() => setShowRSI(!showRSI)}>● RSI</span>
          <span className={`tag ${showVolume ? "" : "off"}`} onClick={() => setShowVolume(!showVolume)}>● Volume</span>
        </div>
        {loading && <div className="pc-loading">A carregar…</div>}
      </div>

      <div className="pc-main" ref={mainRef}></div>
      <div className="pc-rsi" ref={rsiRef}></div>
      <div className="pc-volume" ref={volRef}></div>
    </div>
  );
}
