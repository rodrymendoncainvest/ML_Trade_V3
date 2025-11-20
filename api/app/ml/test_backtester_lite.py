# ml/test_backtester_lite.py

import os
from ml.backtester_lite import BacktesterLite


# BASE_DIR correto → api/data/
BASE_DATA = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "data")
)


def main():
    print("=== TESTE BACKTESTER LITE ===")

    symbol = "ASML.AS"
    model_key = "ASML.AS_lite"

    # confirmar caminho limpo só para debug visual
    clean_path = os.path.join(
        BASE_DATA,
        "clean",
        f"{symbol}_1H_clean.csv"
    )

    print(f"→ A procurar CSV limpo em: {clean_path}")

    bt = BacktesterLite(
        symbol=symbol,
        model_key=model_key,
        seq_len=50
    )

    result = bt.run()

    print("\n=== PRIMEIRAS LINHAS DO RESULTADO ===")
    print(result.head())

    print("\n=== ÚLTIMAS LINHAS DO RESULTADO ===")
    print(result.tail())


if __name__ == "__main__":
    main()
