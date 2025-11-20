# test_pipeline.py

import numpy as np
import pandas as pd

from ml.dataset_builder import DatasetBuilder
from ml.features import FeatureEngineer
from ml.model_trainer import ModelTrainer
from ml.model_inference import ModelInference


def make_synthetic(n=200):
    np.random.seed(42)
    df = pd.DataFrame({
        "open": np.random.rand(n)*100,
        "high": np.random.rand(n)*100,
        "low": np.random.rand(n)*100,
        "close": np.random.rand(n)*100,
        "volume": np.random.rand(n)*1000,
    })
    df["ema_20"] = df["close"].rolling(20).mean()
    df["ema_50"] = df["close"].rolling(50).mean()
    return df


def main():
    print("=== TESTE LSTM ML ===")

    df = make_synthetic()
    df = DatasetBuilder().build(df)
    df = FeatureEngineer().transform(df)

    trainer = ModelTrainer()
    trainer.train(df, "model_1h")

    infer = ModelInference("model_1h")

    last_seq = df.iloc[-50:]
    pred = infer.predict(last_seq)

    print(pred)


if __name__ == "__main__":
    main()
