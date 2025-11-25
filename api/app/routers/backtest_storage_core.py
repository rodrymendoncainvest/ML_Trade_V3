# ============================================================
#  BACKTEST STORAGE CORE — V4
#  Guarda ficheiros JSON com resultados de backtests
# ============================================================

import os
import json
from datetime import datetime


class BacktestStorageCore:
    """
    Guarda automaticamente backtests em:
        storage/backtests/<symbol>/
    """

    def __init__(self, root_dir):
        self.root_dir = root_dir
        os.makedirs(self.root_dir, exist_ok=True)

    # ------------------------------------------------------------
    def _make_symbol_dir(self, symbol):
        symbol_dir = os.path.join(self.root_dir, symbol.upper())
        os.makedirs(symbol_dir, exist_ok=True)
        return symbol_dir

    # ------------------------------------------------------------
    def save(self, symbol: str, tf: str, payload: dict) -> str:
        """
        Guarda um ficheiro JSON do backtest:
            storage/backtests/SYMBOL/SYMBOL_1H_YYYYMMDD_HHMM.json
        """
        symbol = symbol.upper()
        symbol_dir = self._make_symbol_dir(symbol)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{symbol}_{tf}_{timestamp}.json"
        path = os.path.join(symbol_dir, filename)

        # Converter tipos numpy → valores Python
        clean_payload = self._sanitize(payload)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(clean_payload, f, indent=2)

        return path

    # ------------------------------------------------------------
    def _sanitize(self, obj):
        """
        Converte tipos numpy / floats não serializáveis → tipos nativos.
        """
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}

        if isinstance(obj, list):
            return [self._sanitize(v) for v in obj]

        # numpy scalars
        try:
            import numpy as np
            if isinstance(obj, (np.integer, np.int32, np.int64)):
                return int(obj)
            if isinstance(obj, (np.floating, np.float32, np.float64)):
                return float(obj)
        except Exception:
            pass

        return obj
