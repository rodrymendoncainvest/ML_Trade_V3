# ============================================================
#  REPORT V3 — ML_Trade
#  Relatório institucional para modelo V3 / backtester V3
# ============================================================

import pandas as pd
import numpy as np
from sklearn.metrics import confusion_matrix


class ReportV3:

    def __init__(self, symbol: str, variant: str = "v3_multihead"):
        self.symbol = symbol
        self.variant = variant

    # --------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------
    def _drawdown(self, equity):
        eq = np.array(equity)
        peaks = np.maximum.accumulate(eq)
        dd = (eq - peaks) / peaks
        return dd, dd.min()

    def _sharpe(self, returns):
        if returns.std() == 0:
            return 0.0
        return (returns.mean() / returns.std()) * np.sqrt(252)

    def _profit_factor(self, returns):
        gains = returns[returns > 0].sum()
        losses = -returns[returns < 0].sum()
        if losses == 0:
            return np.inf
        return gains / losses

    # --------------------------------------------------------------
    # MAIN REPORT
    # --------------------------------------------------------------
    def generate(self, backtest_result, df_clean):

        equity = np.array(backtest_result["equity_curve"])
        trades = backtest_result["trades"]

        returns = pd.Series(equity).pct_change().fillna(0)

        # ---- Drawdown ----
        dd_curve, max_dd = self._drawdown(equity)

        # ---- Sharpe ----
        sharpe = self._sharpe(returns)

        # ---- Profit factor ----
        pf = self._profit_factor(returns)

        # ---- Winrate ----
        trade_returns = []
        for t in trades:
            trade_returns.append(t["position"] * (t["price"] / df_clean["close"].iloc[0]))

        trade_returns = np.array(trade_returns)
        winrate = (trade_returns > 0).mean() if len(trade_returns) > 0 else 0

        # ---- Regime distribution ----
        regime_counts = pd.Series([t["reason"] for t in trades]).value_counts()

        # ---- Summary ----
        report = {
            "symbol": self.symbol,
            "variant": self.variant,
            "num_trades": len(trades),
            "final_equity": float(equity[-1]),
            "pnl": float(equity[-1] - equity[0]),
            "max_drawdown_pct": float(max_dd * 100),
            "sharpe": float(sharpe),
            "profit_factor": float(pf),
            "winrate": float(winrate * 100),
            "regime_distribution": regime_counts.to_dict(),
        }

        return report
