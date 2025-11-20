# guarda isto num ficheiro: ml/check_labels.py

import os
import pandas as pd

# Caminho para api/data/clean
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "clean"))

symbol = "ASML.AS"
path = os.path.join(BASE, f"{symbol}_1H_clean.csv")

print("A carregar:", path)
df = pd.read_csv(path, index_col=0, parse_dates=True)

# ===========================
# GERAR LABELS COMO NO TREINO
# ===========================
df["future_close"] = df["close"].shift(-1)
df["future_return_pct"] = (df["future_close"] - df["close"]) / df["close"] * 100

df["label"] = pd.qcut(df["future_return_pct"], 5, labels=[0,1,2,3,4])

df = df.dropna(subset=["label"])

print("\n=== Distribuição das Labels ===")
print(df["label"].value_counts().sort_index())

print("\nPercentagens (%)")
print((df["label"].value_counts(normalize=True).sort_index() * 100).round(2))
