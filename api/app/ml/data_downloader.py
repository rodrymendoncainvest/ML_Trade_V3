# data_downloader.py

import os
import pandas as pd
import yfinance as yf

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "history")
os.makedirs(DATA_DIR, exist_ok=True)

def download_asml_1h():
    ticker = "ASML.AS"
    print(f"Descarregar dados 1H de {ticker} via Yahoo Finance...")

    df = yf.download(
        tickers=ticker,
        interval="1h",
        period="730d"   # ~2 anos de histórico
    )

    if df.empty:
        raise RuntimeError("Yahoo Finance devolveu dataset vazio para ASML.AS")

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume"
    })

    df["symbol"] = "ASML.AS"
    df = df.dropna()

    out_path = os.path.join(DATA_DIR, "ASML_AS_1H.csv")
    df.to_csv(out_path, index=True)

    print(f"Dataset guardado em: {out_path}")
    print(df.head())

    return df


if __name__ == "__main__":
    download_asml_1h()
