from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Dict, List, Tuple
import joblib

# raiz do projeto: .../ML_Trade
ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def model_key(symbol: str, tf: str) -> str:
    return f"{symbol.upper()}_{tf}"

def model_path(key: str) -> Path:
    return MODELS_DIR / f"{key}.joblib"

def meta_path(key: str) -> Path:
    return MODELS_DIR / f"{key}.json"

def save_model(key: str, model: Any, meta: Dict[str, Any]) -> str:
    p = model_path(key)
    joblib.dump(model, p)
    m = meta_path(key)
    meta = {**meta, "key": key}
    m.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(p)

def load_model(key: str) -> Tuple[Any, Dict[str, Any]]:
    p = model_path(key)
    if not p.exists():
        raise FileNotFoundError(f"Modelo '{key}' não encontrado em {p}")
    model = joblib.load(p)
    meta = {}
    m = meta_path(key)
    if m.exists():
        meta = json.loads(m.read_text(encoding="utf-8"))
    return model, meta

def list_models() -> List[Dict[str, Any]]:
    out = []
    for f in MODELS_DIR.glob("*.joblib"):
        k = f.stem
        meta = {}
        m = meta_path(k)
        if m.exists():
            meta = json.loads(m.read_text(encoding="utf-8"))
        out.append({"key": k, "path": str(f), "meta": meta})
    return sorted(out, key=lambda d: d["key"])
