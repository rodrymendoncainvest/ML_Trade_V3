# data_downloader.py

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

    Exemplo: ASML.AS_1H.csv
    """
    print(f"Descarregar dados 1H de {ticker} via Yahoo Finance...")

    df = yf.download(
        tickers=ticker,
        interval="1h",
        period=period,
        auto_adjust=False   # manter preços reais sem ajustamentos
    )

    if df.empty:
        raise RuntimeError(f"Yahoo Finance devolveu dataset vazio para {ticker}")

    # normalizar nomes das colunas
    df = df.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }
    )

    df["symbol"] = ticker

    # garantir timezone UTC
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")

    df = df.dropna()
    df = df.sort_index()

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
