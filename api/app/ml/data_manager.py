import os
import sys
import pandas as pd
from pathlib import Path

# ============================================================
#  DIRECTÓRIOS OFICIAIS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[2] / "data"
HISTORY_DIR = BASE_DIR / "history"
CLEAN_DIR   = BASE_DIR / "clean"
FEATURE_DIR = BASE_DIR / "features"

for d in [HISTORY_DIR, CLEAN_DIR, FEATURE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
#  FUNÇÃO: carregar CSV bruto (Yahoo OU TradingView)
# ============================================================

def load_raw(symbol: str) -> pd.DataFrame:
    """
    Carrega CSV bruto gerado pelo data_downloader (Yahoo Finance)
    OU um CSV exportado do TradingView.
    Deteta automaticamente o formato.
    """

    fname = f"{symbol}_1H.csv"
    path = HISTORY_DIR / fname

    if not path.exists():
        raise RuntimeError(f"CSV não encontrado: {path}")

    df = pd.read_csv(path)

    # --------------------------------------------------------
    # CASO 1 — Ficheiro Yahoo Finance (index datetime)
    # --------------------------------------------------------
    if "Price" not in df.columns:
        # Yahoo: datetime está como índice ou como coluna
        if "Unnamed: 0" in df.columns:
            # Yahoo às vezes grava índice com nome estranho
            df = df.rename(columns={"Unnamed: 0": "datetime"})
            df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
            df = df.set_index("datetime")
        elif df.columns[0].lower() in ["datetime", "date", "time"]:
            # Outro formato comum
            df[df.columns[0]] = pd.to_datetime(df[df.columns[0]], utc=True)
            df = df.set_index(df.columns[0])
        else:
            raise RuntimeError("Formato Yahoo desconhecido no CSV.")

        df.index.name = "timestamp"

        # converter numéricas
        for col in ["open","high","low","close","volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df["symbol"] = symbol
        df = df.sort_index()
        return df

    # --------------------------------------------------------
    # CASO 2 — Ficheiro TradingView (Price, Ticker, Datetime)
    # --------------------------------------------------------

    # eliminar as duas primeiras linhas (Ticker / Datetime)
    df = df.iloc[2:].copy()
    df["Price"] = pd.to_datetime(df["Price"], utc=True, errors="coerce")
    df = df.dropna(subset=["Price"])
    df = df.set_index("Price")

    # converter OHLCV para numéricos
    for col in ["open","high","low","close","volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["symbol"] = symbol
    df = df.sort_index()
    return df


# ============================================================
#  FUNÇÃO: limpeza de dados
# ============================================================

def clean_dataset(symbol: str) -> pd.DataFrame:
    df = load_raw(symbol)

    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[df["volume"] > 0]

    market_hours = {
        "EU": ("09:00", "17:30"),
        "US": ("09:30", "16:00"),
        "HK": ("09:30", "16:00"),
    }

    if symbol.endswith(".AS"):
        region = "EU"
    elif symbol.endswith(".US"):
        region = "US"
    elif symbol.endswith(".HK"):
        region = "HK"
    else:
        region = "EU"

    h_start, h_end = market_hours[region]
    df = df.between_time(h_start, h_end)
    df = df.sort_index()

    out_path = CLEAN_DIR / f"{symbol}_1H_clean.csv"
    df.to_csv(out_path)

    return df


# ============================================================
#  CLI
# ============================================================

def run_clean(symbol: str):
    print(f"=== CLEANING {symbol} ===")
    df = clean_dataset(symbol)
    print(df.head())
    print("...")
    print(df.tail())
    print("\nGuardado em:")
    print(CLEAN_DIR / f"{symbol}_1H_clean.csv")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m ml.data_manager SYMBOL")
        sys.exit(1)

    run_clean(sys.argv[1])
