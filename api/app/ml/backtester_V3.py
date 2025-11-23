# ============================================================
#  BACKTESTER V3.7 — ML_Trade (corrigido: inclui FeatureEngineer)
# ============================================================

import os
import numpy as np
import pandas as pd

from app.ml.model_inference_V3 import ModelInferenceV3
from app.ml.signal_engine_V3 import SignalEngineV3
from app.ml.feature_engineer_V3 import FeatureEngineerV3


class BacktesterV3:

    def __init__(self, symbol: str, variant: str = "v3_multihead", risk_mode: str = "moderate"):
        self.symbol = symbol
        self.variant = variant

        self.infer = ModelInferenceV3(symbol, variant)
        self.engine = SignalEngineV3(risk_mode)

        self.initial_equity = 10000.0
        self.equity = self.initial_equity
        self.position = 0.0

        self.equity_curve = []
        self.trades = []

    def _progress_bar(self, idx, total):
        pct = (idx + 1) / total
        bar_len = 30
        filled = int(pct * bar_len)
        bar = "[" + "#" * filled + "." * (bar_len - filled) + "]"
        print(f"\r{bar} {pct*100:5.1f}%  ({idx+1}/{total})", end="", flush=True)

    def run(self):

        print(f"\nRunning backtest for {self.symbol} ({self.variant})...\n")

        # ============================================================
        # CAMINHO CORRIGIDO — sem alterar mais nada no módulo
        # ============================================================
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        clean_path = os.path.join(base_dir, "data", "clean", f"{self.symbol}_1H_clean.csv")

        if not os.path.exists(clean_path):
            raise FileNotFoundError(f"Clean file not found at: {clean_path}")

        df = pd.read_csv(clean_path, index_col=0)
        df.index = pd.to_datetime(df.index)

        # ============================================================
        # NOVO → aplicar Feature Engineering antes do backtest
        # ============================================================
        fe = FeatureEngineerV3()
        df_fe = fe.transform(df)

        prices = df["close"].values
        n = len(df_fe)

        seq = self.infer.seq_len
        step = 3
        start = seq + 100

        if n < start:
            raise RuntimeError(f"Dataset too small for V3 inference (need {start}, have {n})")

        total_iter = (n - start) // step

        self.equity = self.initial_equity
        self.position = 0.0
        self.equity_curve = []
        self.trades = []

        for idx, i in enumerate(range(start, n, step)):

            if idx >= total_iter:
                break

            # usar janela com FEATURES
            window = df_fe.iloc[i - (seq + 100): i]

            prediction = self.infer.predict(window)
            signal = self.engine.generate_signal(prediction)

            price = prices[i]

            if signal["signal"] == "BUY":
                self.position = signal["position"]
                self.trades.append({
                    "timestamp": df.index[i],
                    "signal": "BUY",
                    "position": self.position,
                    "price": price,
                    "reason": signal["reason"]
                })

            elif signal["signal"] == "SELL":
                self.position = -signal["position"]
                self.trades.append({
                    "timestamp": df.index[i],
                    "signal": "SELL",
                    "position": self.position,
                    "price": price,
                    "reason": signal["reason"]
                })

            ret = (prices[i] - prices[i-1]) / prices[i-1]
            self.equity *= (1 + self.position * ret)
            self.equity_curve.append(self.equity)

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
