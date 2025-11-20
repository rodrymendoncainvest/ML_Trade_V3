# test_trainer_lite.py

import os
import sys
import pandas as pd

from ml.model_trainer_lite import ModelTrainerLite

# Caminho correto para api/data
# Estamos em: api/app/ml/test_trainer_lite.py
# Subir 3 níveis → api/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_CLEAN = os.path.join(ROOT, "data", "clean")

def load_clean(symbol: str):
    """
    Lê o CSV limpo do símbolo — exatamente como existe no disco.
    """
    filename = f"{symbol}_1H_clean.csv"
    path = os.path.join(DATA_CLEAN, filename)

    print(f"→ A carregar CSV limpo de: {path}")

    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV limpo não encontrado em: {path}")

    df = pd.read_csv(path, parse_dates=True, index_col=0)
    print(f"Dataset carregado: {len(df)} linhas — {df.shape[1]} colunas")
    return df


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m ml.test_trainer_lite SYMBOL")
        sys.exit(1)

    symbol = sys.argv[1]

    print(f"=== TESTE LSTM LITE: {symbol} ===")

    df = load_clean(symbol)

    trainer = ModelTrainerLite(
        model_key=f"{symbol}_lite",
        sequence_length=50,
        epochs=10,
        lr=1e-3,
        batch_size=32
    )

    model, scaler, features = trainer.train(df)

    print("\n=== TREINO COMPLETO ===")
    print("Modelo:", model)
    print("Scaler:", scaler)
    print("Features:", features)


if __name__ == "__main__":
    main()
