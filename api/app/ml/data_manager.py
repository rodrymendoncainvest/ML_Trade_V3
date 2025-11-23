# ============================================================
#  DATA MANAGER — limpeza robusta para CSVs do yfinance
# ============================================================

import os
import pandas as pd


class DataManager:
    def __init__(self):
        # ROOT = api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.DATA_DIR = os.path.join(self.ROOT, "data")
        self.HIST_DIR = os.path.join(self.DATA_DIR, "history")
        self.CLEAN_DIR = os.path.join(self.DATA_DIR, "clean")

        os.makedirs(self.HIST_DIR, exist_ok=True)
        os.makedirs(self.CLEAN_DIR, exist_ok=True)

    # ------------------------------------------------------------
    # DETEÇÃO AUTOMÁTICA DE MULTI-HEADER
    # ------------------------------------------------------------
    def _is_multi_header(self, df: pd.DataFrame) -> bool:
        if isinstance(df.columns, pd.MultiIndex):
            return True

        vals = df.columns.astype(str)
        if all(v == vals[0] for v in vals):
            return True

        return False

    # ------------------------------------------------------------
    # LOADER ROBUSTO
    # ------------------------------------------------------------
    def _load_raw(self, path: str) -> pd.DataFrame:

        try:
            df = pd.read_csv(path, index_col=0)
        except Exception:
            df = None

        if df is None or self._is_multi_header(df):
            print("[INFO] Multi-header ou CSV sujo detetado. A limpar...")

            raw = pd.read_csv(path, header=None)

            raw = raw[~raw[0].astype(str).str.startswith("Ticker")]
            raw = raw[~raw[0].astype(str).str.startswith("Price")]

            tmp_path = path + ".tmp"
            raw.to_csv(tmp_path, index=False, header=False)

            df = pd.read_csv(tmp_path, index_col=0)
            os.remove(tmp_path)

        df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
        df = df[~df.index.isna()].sort_index()

        return df

    # ------------------------------------------------------------
    # CLEAN PRINCIPAL (usado pelos pipelines antigos)
    # ------------------------------------------------------------
    def clean(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        """
        Versão direta da limpeza, usada pelo PIPELINE SSE.
        Não mexe em ficheiros — só trata o DF em memória.
        """

        df = df_raw.copy()

        # Normalizar colunas
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        required = ["open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df[required]

        # filtros básicos
        df = df.dropna()
        df = df[(df["high"] >= df["low"]) & (df["volume"] >= 0)]
        df = df.sort_index()

        return df

    # ------------------------------------------------------------
    # CLEAN SYMBOL (mantido igual, baseado em ficheiros .csv)
    # ------------------------------------------------------------
    def clean_symbol(self, symbol: str, tf: str = "1H"):
        file_raw = os.path.join(self.HIST_DIR, f"{symbol}_{tf}.csv")
        file_clean = os.path.join(self.CLEAN_DIR, f"{symbol}_{tf}_clean.csv")

        if not os.path.exists(file_raw):
            raise FileNotFoundError(f"Raw file not found: {file_raw}")

        df = self._load_raw(file_raw)

        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        required = ["open", "high", "low", "close", "volume"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df = df[required]
        df["symbol"] = symbol

        df = df.dropna()
        df = df[(df["high"] >= df["low"]) & (df["volume"] >= 0)]
        df = df.sort_index()

        df.to_csv(file_clean)
        print(f"[OK] Clean saved: {file_clean}")
        print(df.head())

        return df
