import torch
from ml_core.model_core import ModelCore
from ml_core.config_core import NUM_FEATURES, SEQ_LEN

# Criar input falso para testar (batch=1, seq_len, num_features)
fake_input = torch.randn(1, SEQ_LEN, NUM_FEATURES)

model = ModelCore()

try:
    output = model(fake_input)
    print("OK! Modelo compilou e fez forward pass.")
    print("Output:", output)
except Exception as e:
    print("ERRO:", e)
