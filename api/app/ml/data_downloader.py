# data_downloader.py
# Downloader 1H estável — remove multi-headers do Yahoo Finance

import os
import pandas as pd
import yfinance as yf

# Pasta onde ficam os históricos brutos (raw)
DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data", "history")
)
os.makedirs(DATA_DIR, exist_ok=True)


def download_1h(ticker: str, period: str = "730d") -> pd.DataFrame:
    """
    Descarrega dados 1H de um ticker via Yahoo Finance e guarda em:
        api/data/history/{TICKER}_1H.csv

    O Yahoo às vezes devolve CSV com multi-header (duas linhas).
    Este módulo normaliza sempre para:
        index, open, high, low, close, volume, symbol
    """

    print(f"Descarregar dados 1H de {ticker} via Yahoo Finance...")

    df = yf.download(
        tickers=ticker,
        interval="1h",
        period=period,
        auto_adjust=False
    )

    if df.empty:
        raise RuntimeError(f"Yahoo Finance devolveu dataset vazio para {ticker}")

    # ------------------------------
    # NORMALIZAÇÃO DE COLUNAS
    # ------------------------------
    # Alguns tickers vêm com MultiIndex (ex: ('Close','ASML.AS'))
    # Vamos sempre achatar para um único header.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

    # Garantir que só ficam as colunas úteis
    keep = ["open", "high", "low", "close", "volume"]
    df = df[keep]

    # Coluna símbolo
    df["symbol"] = ticker

    # Garantir timezone consistente
    try:
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
    except Exception:
        # Em caso de CSV malformatado, forçar parse
        df.index = pd.to_datetime(df.index, utc=True, errors="coerce")

    df = df.dropna()
    df = df.sort_index()

    # ------------------------------
    # GUARDA EM CSV
    # ------------------------------
    filename = f"{ticker}_1H.csv"
    out_path = os.path.join(DATA_DIR, filename)

    df.to_csv(out_path, index=True)

    print(f"Dataset guardado em: {out_path}")
    print(df.head())

    return df


def download_asml_1h() -> pd.DataFrame:
    """Wrapper rápido para ASML.AS."""
    return download_1h("ASML.AS")


if __name__ == "__main__":
    download_asml_1h()
