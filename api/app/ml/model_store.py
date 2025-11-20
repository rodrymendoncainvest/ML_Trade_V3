# model_store.py

import os
import joblib
import torch

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def save_model(model_key, model, scaler, feature_cols):
    """
    Guarda modelo PyTorch + scaler + metadata.
    """

    # Guardar modelo
    torch.save(model.state_dict(), os.path.join(MODEL_DIR, f"{model_key}.pt"))

    # Guardar scaler
    joblib.dump(scaler, os.path.join(MODEL_DIR, f"{model_key}.scaler"))

    # Guardar features e metadata
    metadata = {
        "feature_cols": feature_cols,
        "n_features": len(feature_cols)
    }
    joblib.dump(metadata, os.path.join(MODEL_DIR, f"{model_key}.meta"))


def load_model(model_key, model_class):
    """
    Carrega modelo, scaler, feature_cols e n_features.
    """

    model_path = os.path.join(MODEL_DIR, f"{model_key}.pt")
    scaler_path = os.path.join(MODEL_DIR, f"{model_key}.scaler")
    meta_path = os.path.join(MODEL_DIR, f"{model_key}.meta")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modelo '{model_key}' não encontrado")

    # Carregar metadata
    meta = joblib.load(meta_path)
    feature_cols = meta["feature_cols"]
    n_features = meta["n_features"]

    # Criar modelo
    model = model_class(n_features=n_features)
    model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
    model.eval()

    # Carregar scaler
    scaler = joblib.load(scaler_path)

    return model, scaler, feature_cols, n_features
