# ============================================================
#  SIGNAL ENGINE V3 — ML_Trade (com modos de risco, coerente
#  com o output real do ModelInferenceV3)
# ============================================================

import numpy as np


class SignalEngineV3:
    """
    Engine responsável por transformar as previsões do modelo
    (multi-head: direction + trend) em sinais de trading.

    Modos de risco:
      - aggressive
      - moderate (default)
      - conservative

    100% compatível com output do ModelInferenceV3:
        {
            "direction_probs": [...],
            "trend_probs": [...],
            "direction": 0/1,
            "trend": 0/1/2
        }
    """

    def __init__(self, risk_mode: str = "moderate"):
        valid_modes = ["aggressive", "moderate", "conservative"]
        if risk_mode not in valid_modes:
            raise ValueError(f"Invalid risk_mode: {risk_mode}")

        self.risk_mode = risk_mode

        # ----------------------------------------
        # THRESHOLDS POR MODO
        # ----------------------------------------
        if risk_mode == "aggressive":
            self.dir_th = 0.52
            self.trend_th = 0.40
            self.max_pos = 1.00

        elif risk_mode == "moderate":
            self.dir_th = 0.60
            self.trend_th = 0.50
            self.max_pos = 0.70

        else:  # conservative
            self.dir_th = 0.70
            self.trend_th = 0.60
            self.max_pos = 0.40

    # -----------------------------------------------------------
    # FUNÇÃO PRINCIPAL
    # -----------------------------------------------------------
    def generate_signal(self, prediction: dict):
        """
        Recebe:
            prediction = {
                "direction_probs": [...],
                "trend_probs": [...],
                "direction": 0/1,
                "trend": 0/1/2
            }

        Retorna dict:
            {
                "signal": "BUY"/"SELL"/"HOLD",
                "position": float,
                "reason": str
            }
        """

        dir_probs = prediction["direction_probs"]
        trend_probs = prediction["trend_probs"]

        # Extrair probabilidades
        dir_dn = float(dir_probs[0])
        dir_up = float(dir_probs[1])

        tr_dn = float(trend_probs[0])
        tr_up = float(trend_probs[1])
        tr_rg = float(trend_probs[2])

        # Medidas auxiliares
        direction_conf = abs(dir_up - dir_dn)
        trend_bias = tr_up - tr_dn
        combined = 0.6 * direction_conf + 0.4 * abs(trend_bias)

        # --------------------------
        # BUY
        # --------------------------
        if dir_up > self.dir_th and tr_up > self.trend_th:
            pos = min(max(combined * self.max_pos, 0.0), self.max_pos)
            return {
                "signal": "BUY",
                "position": pos,
                "reason": (
                    f"BUY: dir_up={dir_up:.3f}, tr_up={tr_up:.3f}, "
                    f"dir_conf={direction_conf:.3f}, trend_bias={trend_bias:.3f}"
                )
            }

        # --------------------------
        # SELL
        # --------------------------
        if dir_dn > self.dir_th and tr_dn > self.trend_th:
            pos = min(max(combined * self.max_pos, 0.0), self.max_pos)
            return {
                "signal": "SELL",
                "position": pos,
                "reason": (
                    f"SELL: dir_dn={dir_dn:.3f}, tr_dn={tr_dn:.3f}, "
                    f"dir_conf={direction_conf:.3f}, trend_bias={trend_bias:.3f}"
                )
            }

        # --------------------------
        # HOLD
        # --------------------------
        return {
            "signal": "HOLD",
            "position": 0.0,
            "reason": (
                f"HOLD: dir_conf={direction_conf:.3f}, trend_bias={trend_bias:.3f}, "
                f"no threshold match"
            )
        }
