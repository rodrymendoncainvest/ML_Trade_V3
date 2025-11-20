import os
import sys
import pandas as pd
from pathlib import Path


# ============================================================
#  DIRECTÓRIOS OFICIAIS (fixos e centralizados)
# ============================================================

# Este ficheiro está em: api/app/ml/data_manager.py
# Subimos 2 níveis -> api/
BASE_DIR = Path(__file__).resolve().parents[2] / "data"

HISTORY_DIR = BASE_DIR / "history"
CLEAN_DIR   = BASE_DIR / "clean"
FEATURE_DIR = BASE_DIR / "features"

for d in [HISTORY_DIR, CLEAN_DIR, FEATURE_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
#  FUNÇÃO: carregar CSV bruto (formato TradingView)
# ============================================================

def load_raw(symbol: str) -> pd.DataFrame:
    """
    Lê o CSV bruto gerado pelo data_downloader.
    O formato padrão tem a coluna 'Price' contendo os timestamps.
    A primeira linha é 'Ticker', a segunda é 'Datetime'.

    Exemplo do CSV:
        Price, close, high, low, open, volume, symbol
        Ticker, ASML.AS, ASML.AS, ...
        Datetime, ...
        2023-01-13 08:00:00+00:00, 605.29, ...

    Esta função normaliza tudo e devolve um DataFrame com índice datetime.
    """

    fname = symbol.replace(".", "_") + "_1H.csv"
    path = HISTORY_DIR / fname

    if not path.exists():
        raise RuntimeError(f"CSV não encontrado: {path}")

    df = pd.read_csv(path, dtype=str)

    # Garantir coluna "Price" existe (TradingView exporta assim)
    if "Price" not in df.columns:
        raise RuntimeError("CSV inesperado: falta coluna 'Price' (timestamp).")

    # Remover 2 primeiras linhas inúteis ("Ticker", "Datetime")
    df = df.iloc[2:].copy()

    # Converter timestamps
    df["Price"] = pd.to_datetime(df["Price"], utc=True, errors="coerce")

    # Dropar linhas inválidas
    df = df.dropna(subset=["Price"])

    # Tornar o timestamp o índice
    df = df.set_index("Price")

    # Converter numéricas
    numeric_cols = ["open", "high", "low", "close", "volume"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Garantir que o símbolo está presente
    df["symbol"] = symbol

    # Ordenar por tempo
    df = df.sort_index()

    return df


# ============================================================
#  FUNÇÃO: limpeza de dados (drop missing, ordenar, horário)
# ============================================================

def clean_dataset(symbol: str) -> pd.DataFrame:
    """
    Limpeza do dataset:
      - remove linhas sem OHLC
      - remove volume = 0 (pré-mercado TradingView)
      - filtra por horário do mercado correto (config por símbolo)
      - ordena e remove duplicados
    """

    df = load_raw(symbol)

    # Remover linhas que não tenham preços
    df = df.dropna(subset=["open", "high", "low", "close"])

    # Remover pré-mercado / after-hours (volume=0)
    df = df[df["volume"] > 0]

    # Configurar horário por mercado
    market_hours = {
        "EU": ("09:00", "17:30"),
        "US": ("09:30", "16:00"),
        "HK": ("09:30", "16:00"),
    }

    # Detectar região automaticamente
    if symbol.endswith(".AS"):   # Euronext Amsterdam
        region = "EU"
    elif symbol.endswith(".US"): # USA
        region = "US"
    elif symbol.endswith(".HK"): # Hong Kong
        region = "HK"
    else:
        region = "EU"  # default

    h_start, h_end = market_hours[region]

    # Aplicar filtragem
    df = df.between_time(h_start, h_end)

    # Ordenar timestamps
    df = df.sort_index()

    # Guardar CSV limpo
    out_path = CLEAN_DIR / (symbol.replace(".", "_") + "_1H_clean.csv")
    df.to_csv(out_path)

    return df


# ============================================================
#  COMMAND-LINE INTERFACE
# ============================================================

def run_clean(symbol: str):
    print(f"=== CLEANING {symbol} ===")
    df = clean_dataset(symbol)
    print(df.head())
    print("...")
    print(df.tail())
    print("\nGuardado em:")
    print(CLEAN_DIR / (symbol.replace('.', '_') + "_1H_clean.csv"))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python -m ml.data_manager SYMBOL")
        sys.exit(1)

    run_clean(sys.argv[1])
