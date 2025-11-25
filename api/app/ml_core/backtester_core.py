# ============================================================
#  BACKTESTER CORE — V4 (com integração BacktestStorage)
# ============================================================

import numpy as np

class BacktesterCore:
    def __init__(self, symbol, storage=None, tf="1H"):
        self.symbol = symbol
        self.storage = storage
        self.tf = tf

    # --------------------------------------------------------
    # Estratégia simples baseada no sinal histórico
    # --------------------------------------------------------
    def run(self, df_clean):

        prices = df_clean["close"].values
        returns = df_clean["close"].pct_change().fillna(0).values

        equity = 1.0
        equity_curve = [equity]
        position = 0  # -1 short, 1 long, 0 flat
        trades = []

        for i in range(1, len(prices)):

            r = returns[i]

            # regra simples: se retorno > 0 → long; se < 0 → short
            signal = 1 if r > 0 else -1

            if signal != position:
                # fechar posição anterior
                if position == 1:
                    trades.append({"type": "close_long", "price": float(prices[i])})
                if position == -1:
                    trades.append({"type": "close_short", "price": float(prices[i])})

                # abrir nova posição
                if signal == 1:
                    trades.append({"type": "open_long", "price": float(prices[i])})
                else:
                    trades.append({"type": "open_short", "price": float(prices[i])})

                position = signal

            # atualizar equity
            equity *= (1 + position * r)
            equity_curve.append(equity)

        final_value = float(equity)
        num_trades = len(trades)

        payload = {
            "symbol": self.symbol,
            "tf": self.tf,
            "final_value": final_value,
            "num_trades": num_trades,
            "equity_curve": equity_curve,
            "trades": trades,
        }

        # salvar se o storage estiver presente
        if self.storage:
            path = self.storage.save(self.symbol, self.tf, payload)
            payload["saved_to"] = path

        return payload
