# ============================================================
#  SIGNAL ENGINE V3.5 — afinado para abrir mais sinais reais
# ============================================================

import numpy as np


class SignalEngineV3:

    def __init__(self, risk_mode: str = "moderate"):
        valid = ["aggressive", "moderate", "conservative"]
        if risk_mode not in valid:
            raise ValueError(f"Invalid risk_mode: {risk_mode}")

        self.risk_mode = risk_mode

        if risk_mode == "aggressive":
            self.dir_th = 0.50
            self.trend_th = 0.35
            self.max_pos = 1.00

        elif risk_mode == "moderate":
            self.dir_th = 0.55      # <-- afinado
            self.trend_th = 0.45    # <-- afinado
            self.max_pos = 0.70

        else:  # conservative
            self.dir_th = 0.70
            self.trend_th = 0.60
            self.max_pos = 0.40

    # -----------------------------------------------------------
    def generate_signal(self, p: dict):

        dir_dn = float(p["direction_probs"][0])
        dir_up = float(p["direction_probs"][1])

        tr_dn = float(p["trend_probs"][0])
        tr_up = float(p["trend_probs"][1])
        tr_rg = float(p["trend_probs"][2])

        direction_conf = abs(dir_up - dir_dn)
        trend_bias = tr_up - tr_dn

        combined = 0.6 * direction_conf + 0.4 * abs(trend_bias)
        combined = max(min(combined, 1.0), 0.0)

        # BUY
        if dir_up > self.dir_th and tr_up > self.trend_th:
            pos = min(combined * self.max_pos, self.max_pos)
            return {
                "signal": "BUY",
                "position": pos,
                "reason": (
                    f"BUY: dir_up={dir_up:.3f}, tr_up={tr_up:.3f}, "
                    f"conf={direction_conf:.3f}, bias={trend_bias:.3f}"
                ),
            }

        # SELL
        if dir_dn > self.dir_th and tr_dn > self.trend_th:
            pos = min(combined * self.max_pos, self.max_pos)
            return {
                "signal": "SELL",
                "position": pos,
                "reason": (
                    f"SELL: dir_dn={dir_dn:.3f}, tr_dn={tr_dn:.3f}, "
                    f"conf={direction_conf:.3f}, bias={trend_bias:.3f}"
                ),
            }

        # HOLD
        return {
            "signal": "HOLD",
            "position": 0.0,
            "reason": (
                f"HOLD: conf={direction_conf:.3f}, bias={trend_bias:.3f}, "
                f"no match"
            ),
        }
