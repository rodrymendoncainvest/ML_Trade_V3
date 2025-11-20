# ml/test_inference_lite.py

import os
import pandas as pd
from ml.model_inference_lite import ModelInferenceLite


def load_clean(symbol: str):

    # caminho correto da pasta data/clean
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clean"))

    path = os.path.join(base, f"{symbol.replace('.', '_')}_1H_clean.csv")

    print(f"→ A carregar CSV limpo de: {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV limpo não encontrado em: {path}")

    return pd.read_csv(path, parse_dates=True, index_col=0)


def main():

    symbol = "ASML.AS"

    # carregar dataset limpo
    df = load_clean(symbol)

    # carregar inferência
    infer = ModelInferenceLite(model_key=f"{symbol}_lite")

    # correr inferência
    result = infer.predict(df, seq_len=50)

    print("\n=== RESULTADO DA INFERÊNCIA ===")
    print(result)


if __name__ == "__main__":
    main()
