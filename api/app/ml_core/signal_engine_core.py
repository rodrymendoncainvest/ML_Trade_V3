# ============================================================
# SIGNAL ENGINE CORE — versão moderna, alinhada com MLCore
# ============================================================

class SignalEngineCore:

    def __init__(self, mode: str = "moderate"):
        mode = mode.lower()

        if mode == "conservative":
            self.long_th = 0.002
            self.short_th = 0.002

        elif mode == "aggressive":
            self.long_th = 0.0005
            self.short_th = 0.0005

        else:  # moderate (default)
            self.long_th = 0.001
            self.short_th = 0.001

    # ------------------------------------------------------------
    # Gera sinal baseado no predicted_return
    # ------------------------------------------------------------
    def generate(self, predicted_return: float):
        """
        predicted_return é o output direto do InferenceCore.
        """

        if predicted_return > self.long_th:
            signal = "buy"
            strength = abs(predicted_return)

        elif predicted_return < -self.short_th:
            signal = "sell"
            strength = abs(predicted_return)

        else:
            signal = "hold"
            strength = 0.0

        return {
            "signal": signal,
            "strength": float(strength),
            "predicted_return": float(predicted_return)
        }
