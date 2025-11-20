# ml/test_inference_lite.py

import os
import pandas as pd
from ml.model_inference_lite import ModelInferenceLite


BASE_DATA = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)

def load_clean(symbol: str):
    # caminho correto e final
    path = os.path.join(
        BASE_DATA,
        "clean",
        f"{symbol}_1H_clean.csv"   # <-- EXACTAMENTE O QUE EXISTE NO DISCO
    )

    print(f"→ A carregar CSV limpo de: {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV limpo não encontrado em: {path}")

    return pd.read_csv(path, index_col=0, parse_dates=True)


def main():
    symbol = "ASML.AS"
    model_key = "ASML.AS_lite"

    df = load_clean(symbol)

    infer = ModelInferenceLite(model_key=model_key)

    result = infer.predict(df, seq_len=50)

    print("\n=== RESULTADO DA INFERÊNCIA ===")
    print(result)


if __name__ == "__main__":
    main()
