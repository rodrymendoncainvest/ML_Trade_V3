import os
from pathlib import Path
import pandas as pd

from ml.model_inference_lite import ModelInferenceLite
from ml.feature_engineer_lite import FeatureEngineerLite


class BacktesterLite:
    """
    Backtesting simples para modelos LSTM Lite.
    - Reconstrói features
    - Recorre ao modelo para cada timestamp
    - Gera sinais (compra/venda/neutral)
    - Simula execução e calcula P/L
    """

    def __init__(self, symbol: str, model_key: str, seq_len: int = 50):
        self.symbol = symbol
        self.seq_len = seq_len
        self.model_key = model_key

        # -----------------------------------------------------------
        # BASE_DIR CORRETO: api/data
        # -----------------------------------------------------------
        base_dir = Path(__file__).resolve().parents[2] / "data"

        # ficheiro limpo correto (COM PONTO)
        clean_name = f"{symbol}_1H_clean.csv"
        self.clean_path = base_dir / "clean" / clean_name

        # pasta backtest consistente
        self.backtest_dir = base_dir / "backtest"
        self.backtest_dir.mkdir(parents=True, exist_ok=True)

        # ficheiro final do backtest (COM PONTO)
        self.result_path = self.backtest_dir / f"{symbol}_backtest.csv"

        # componentes
        self.engineer = FeatureEngineerLite()
        self.infer = ModelInferenceLite(model_key=model_key)

    # ------------------------------------------------------------------
    def load_clean(self) -> pd.DataFrame:
        if not self.clean_path.exists():
            raise FileNotFoundError(f"CSV limpo não encontrado: {self.clean_path}")

        df = pd.read_csv(self.clean_path, index_col=0, parse_dates=True)
        return df

    # ------------------------------------------------------------------
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_feat = self.engineer.add_all_features(df.copy())

        if len(df_feat) <= self.seq_len:
            print(f"[BacktesterLite] Dataset com poucas linhas após features: {len(df_feat)}")
            return pd.DataFrame(columns=["timestamp", "close", "signal", "class", "prob"])

        rows = []

        for ts in df_feat.index[self.seq_len:]:
            window = df_feat.loc[:ts].iloc[-self.seq_len:]

            try:
                pred = self.infer.predict(window, seq_len=self.seq_len)
            except Exception:
                continue

            if pred["class"] >= 3:
                action = "compra"
            elif pred["class"] <= 1:
                action = "venda"
            else:
                action = "neutral"

            rows.append({
                "timestamp": ts,
                "close": df.loc[ts, "close"],
                "signal": action,
                "class": pred["class"],
                "prob": max(pred["probs"]),
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    def simulate(self, df_signals: pd.DataFrame) -> pd.DataFrame:
        df = df_signals.copy()

        if df.empty:
            return df

        df["pnl"] = 0.0
        position = "flat"
        entry_price = None

        for i in range(1, len(df)):
            sig = df.iloc[i]["signal"]
            price = df.iloc[i]["close"]

            if position == "flat":
                if sig == "compra":
                    position = "long"
                    entry_price = price
                elif sig == "venda":
                    position = "short"
                    entry_price = price

            elif position == "long":
                if sig == "venda":
                    pnl = price - entry_price
                    df.iloc[i, df.columns.get_loc("pnl")] = pnl
                    position = "short"
                    entry_price = price
                elif sig == "neutral":
                    pnl = price - entry_price
                    df.iloc[i, df.columns.get_loc("pnl")] = pnl
                    position = "flat"
                    entry_price = None

            elif position == "short":
                if sig == "compra":
                    pnl = entry_price - price
                    df.iloc[i, df.columns.get_loc("pnl")] = pnl
                    position = "long"
                    entry_price = price
                elif sig == "neutral":
                    pnl = entry_price - price
                    df.iloc[i, df.columns.get_loc("pnl")] = pnl
                    position = "flat"
                    entry_price = None

        df["equity"] = df["pnl"].cumsum()
        return df

    # ------------------------------------------------------------------
    def run(self) -> pd.DataFrame:
        df = self.load_clean()
        print(f"[BacktesterLite] Dataset limpo: {len(df)} linhas")

        df_signals = self.generate_signals(df)
        print(f"[BacktesterLite] Nº de sinais gerados: {len(df_signals)}")

        if df_signals.empty:
            print("\n[BacktesterLite] Nenhum sinal gerado.")
            df_signals.to_csv(self.result_path)
            print(f"Backtest (vazio) guardado em → {self.result_path}")
            return df_signals

        result = self.simulate(df_signals)

        result.to_csv(self.result_path)
        print(f"\nBacktest completo → {self.result_path}")

        total = float(result["equity"].iloc[-1]) if "equity" in result else 0.0
        winrate = (result["pnl"] > 0).mean() * 100 if "pnl" in result else 0.0

        print(f"P/L total: {total:.2f}")
        print(f"Winrate: {winrate:.2f}%")

        return result
