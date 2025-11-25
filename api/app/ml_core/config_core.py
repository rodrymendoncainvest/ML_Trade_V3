# ============================================================
#  ML_Trade V4 — CONFIG CORE
# ============================================================

import os

# ----------------------------------------------------------------
# Resolver caminhos absolutíssimos (BASE_DIR = api/)
# ----------------------------------------------------------------

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

# Pastas centrais (armazenamento consistente)
BASE_STORAGE = os.path.join(BASE_DIR, "storage")

MODELS_DIR = os.path.join(BASE_STORAGE, "models")
SCALERS_DIR = os.path.join(BASE_STORAGE, "scalers")
META_DIR = os.path.join(BASE_STORAGE, "meta")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(SCALERS_DIR, exist_ok=True)
os.makedirs(META_DIR, exist_ok=True)

# ----------------------------------------------------------------
# Hyperparams centrais
# ----------------------------------------------------------------

NUM_FEATURES = 22
SEQ_LEN = 55

HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.2

FEATURE_ORDER = [
    "open","high","low","close","volume",
    "rsi","macd","macd_signal","macd_hist",
    "sma_fast","sma_slow","ema_fast","ema_slow",
    "stoch_k","stoch_d","williams_r","roc","cci",
    "atr","obv","returns","volatility",
]

assert len(FEATURE_ORDER) == NUM_FEATURES

EPOCHS = 25
LEARNING_RATE = 0.001
BATCH_SIZE = 64
SHUFFLE = True

EARLY_STOPPING_PATIENCE = 5
EARLY_STOPPING_MIN_DELTA = 1e-5

OUTPUT_TYPE = "regression"

BASE_THRESHOLD = 0.002
