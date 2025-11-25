# ============================================================
# REPORT CORE — relatório estatístico para o MLCore
# ============================================================

import numpy as np
import pandas as pd


class ReportCore:

    # --------------------------------------------------------
    def generate(self, backtest_result: dict, df_clean: pd.DataFrame):
        """
        Gera um dicionário de métricas e estatísticas baseado no resultado
        do BacktesterCore.
        """

        equity = backtest_result.get("equity_curve", [])
        trades = backtest_result.get("trades", [])
        final_value = backtest_result.get("final_value", 10000.0)

        # Garantir arrays numpy
        equity = np.array(equity, dtype=float)

        # Se não tiver equity, devolver relatório vazio mas estruturado
        if len(equity) < 2:
            return {
                "ok": False,
                "reason": "Equity curve vazia",
                "equity_curve": equity.tolist(),
                "trades": trades,
                "stats": {},
            }

        # --------------------------------------------------------
        # MÉTRICAS PRINCIPAIS
        # --------------------------------------------------------

        start_val = equity[0]
        end_val = equity[-1]

        total_return = (end_val / start_val) - 1.0

        # Annualized return (assume 365 dias, 24 períodos por dia)
        periods_per_year = 365 * 24
        years = len(equity) / periods_per_year

        if years > 0:
            annualized_return = (end_val / start_val) ** (1 / years) - 1
        else:
            annualized_return = 0.0

        # Volatilidade
        returns = pd.Series(equity).pct_change().dropna()
        volatility = returns.std() * np.sqrt(periods_per_year)

        # Sharpe ratio (risk-free ~ 0)
        sharpe = (returns.mean() * periods_per_year) / (volatility + 1e-12)

        # Max Drawdown
        roll_max = np.maximum.accumulate(equity)
        dd = (equity - roll_max) / roll_max
        max_drawdown = dd.min()

        # Trades
        num_trades = len(trades)
        if num_trades > 0:
            wins = [t for t in trades if t["pnl"] > 0]
            winrate = len(wins) / num_trades
            avg_pnl = np.mean([t["pnl"] for t in trades])
        else:
            winrate = 0.0
            avg_pnl = 0.0

        stats = {
            "total_return": float(total_return),
            "annualized_return": float(annualized_return),
            "volatility": float(volatility),
            "sharpe": float(sharpe),
            "max_drawdown": float(max_drawdown),
            "num_trades": int(num_trades),
            "winrate": float(winrate),
            "avg_pnl": float(avg_pnl),
            "final_equity": float(end_val),
        }

        return {
            "ok": True,
            "equity_curve": equity.tolist(),
            "trades": trades,
            "stats": stats
        }
