# ============================================================
#  BACKTESTER V3.6 — ML_Trade
#  - Janelas seguras (>=144)
#  - Compatível com FeatureEngineerV3
#  - Progress bar correta
# ============================================================

import numpy as np
import pandas as pd
from ml.model_inference_V3 import ModelInferenceV3
from ml.signal_engine_V3 import SignalEngineV3


class BacktesterV3:

    def __init__(self, symbol: str, variant: str = "v3_multihead", risk_mode: str = "moderate"):
        self.symbol = symbol
        self.variant = variant

        # inference + signals
        self.infer = ModelInferenceV3(symbol, variant)
        self.engine = SignalEngineV3(risk_mode)

        # account
        self.initial_equity = 10000.0
        self.equity = self.initial_equity
        self.position = 0.0

        # logs
        self.equity_curve = []
        self.trades = []


    # -----------------------------------------------------------
    # Barra de progresso
    # -----------------------------------------------------------
    def _progress_bar(self, idx, total):
        pct = (idx + 1) / total
        bar_len = 30
        filled = int(pct * bar_len)
        bar = "[" + "#" * filled + "." * (bar_len - filled) + "]"
        print(f"\r{bar} {pct*100:5.1f}%  ({idx+1}/{total})", end="", flush=True)


    # -----------------------------------------------------------
    # EXECUTAR BACKTEST
    # -----------------------------------------------------------
    def run(self):

        print(f"\nRunning backtest for {self.symbol} ({self.variant})...\n")

        # carregar dados limpos
        df = pd.read_csv(f"../data/clean/{self.symbol}_1H_clean.csv", index_col=0)
        df.index = pd.to_datetime(df.index)

        prices = df["close"].values
        n = len(df)

        seq = self.infer.seq_len        # 144
        step = 3                       # a cada 3h
        start = seq + 100              # garantir Features V3 estáveis

        if n < start:
            raise RuntimeError(f"Dataset too small for V3 inference (need {start}, have {n})")

        total_iter = (n - start) // step

        # reset
        self.equity = self.initial_equity
        self.position = 0.0
        self.equity_curve = []
        self.trades = []

        # -------------------------------------------------------
        # LOOP
        # -------------------------------------------------------
        for idx, i in enumerate(range(start, n, step)):

            if idx >= total_iter:
                break

            # janela sempre >=144 com 100 de warmup para FE
            window = df.iloc[i - (seq + 100): i]

            # inferência
            prediction = self.infer.predict(window)

            # gerar sinal
            signal = self.engine.generate_signal(prediction)

            # preço atual
            price = prices[i]

            # -----------------------------------------------
            # EXECUTAR SINAL
            # -----------------------------------------------
            if signal["signal"] == "BUY":
                self.position = signal["position"]
                self.trades.append({
                    "timestamp": window.index[-1],
                    "signal": "BUY",
                    "position": self.position,
                    "price": price,
                    "reason": signal["reason"]
                })

            elif signal["signal"] == "SELL":
                self.position = -signal["position"]
                self.trades.append({
                    "timestamp": window.index[-1],
                    "signal": "SELL",
                    "position": self.position,
                    "price": price,
                    "reason": signal["reason"]
                })

            # atualizar equity
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            self.equity *= (1 + self.position * ret)
            self.equity_curve.append(self.equity)

            # barra
            self._progress_bar(idx, total_iter)


        print("\n\nBacktest complete.\n")

        return {
            "status": "OK",
            "final_equity": self.equity,
            "pnl": self.equity - self.initial_equity,
            "num_trades": len(self.trades),
            "equity_curve": self.equity_curve,
            "trades": self.trades,
        }
