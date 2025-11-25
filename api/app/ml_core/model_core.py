# ============================================================
#  ML_Trade V4 — PatchTST ModelCore
#  - Transformer moderno optimizado para séries temporais
#  - Substitui totalmente o LSTM
#  - Compatível com o TrainerCore e InferenceCore V4
# ============================================================

import torch
import torch.nn as nn
import math

from .config_core import NUM_FEATURES, SEQ_LEN


# ============================================================
#  BLOCO BASICO: FeedForward
# ============================================================

class FeedForward(nn.Module):
    def __init__(self, dim, hidden_dim, dropout=0.1):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, dim)
        )

    def forward(self, x):
        return self.fc(x)


# ============================================================
#  BLOCO: Multi-Head Attention
# ============================================================

class MultiHeadAttention(nn.Module):
    def __init__(self, dim, heads=4, dropout=0.1):
        super().__init__()
        self.attn = nn.MultiheadAttention(embed_dim=dim, num_heads=heads, dropout=dropout, batch_first=True)

    def forward(self, x):
        out, _ = self.attn(x, x, x)
        return out


# ============================================================
#  BLOCO: Transformer Encoder Layer
# ============================================================

class EncoderLayer(nn.Module):
    def __init__(self, dim, heads=4, ff_hidden=256, dropout=0.1):
        super().__init__()

        self.attn = MultiHeadAttention(dim, heads, dropout)
        self.norm1 = nn.LayerNorm(dim)

        self.ff = FeedForward(dim, ff_hidden, dropout)
        self.norm2 = nn.LayerNorm(dim)

    def forward(self, x):
        x = self.norm1(x + self.attn(x))
        x = self.norm2(x + self.ff(x))
        return x


# ============================================================
#  Patch Embedding (patchify 1D)
# ============================================================

class PatchEmbedding(nn.Module):
    def __init__(self, seq_len=55, num_features=22, patch_size=5, dim=128):
        super().__init__()

        assert seq_len % patch_size == 0, "SEQ_LEN deve ser divisível por PATCH_SIZE."

        self.num_patches = seq_len // patch_size
        self.patch_size = patch_size
        self.dim = dim

        self.proj = nn.Linear(patch_size * num_features, dim)

    def forward(self, x):
        """
        x shape: (batch, seq_len, num_features)
        """
        B, S, F = x.shape

        x = x.reshape(B, self.num_patches, self.patch_size * F)
        x = self.proj(x)

        return x  # (batch, num_patches, dim)


# ============================================================
#  PatchTST PRINCIPAL
# ============================================================

class ModelCore(nn.Module):
    def __init__(
        self,
        seq_len=SEQ_LEN,
        num_features=NUM_FEATURES,
        patch_size=5,
        dim=128,
        depth=3,
        heads=4,
        ff_hidden=256,
        dropout=0.1,
    ):
        super().__init__()

        self.patch_embed = PatchEmbedding(seq_len, num_features, patch_size, dim)

        self.encoder_layers = nn.ModuleList([
            EncoderLayer(dim, heads, ff_hidden, dropout)
            for _ in range(depth)
        ])

        # Para regressão → 1 valor
        self.fc = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim),
            nn.GELU(),
            nn.Linear(dim, 1)
        )

        self._init_weights()

    # ------------------------------------------------------------
    # Xavier init
    # ------------------------------------------------------------
    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    # ------------------------------------------------------------
    # Forward Pass
    # ------------------------------------------------------------
    def forward(self, x):
        """
        x: (batch, SEQ_LEN, NUM_FEATURES)
        """

        x = self.patch_embed(x)          # (B, num_patches, dim)

        for layer in self.encoder_layers:
            x = layer(x)

        # tirar média dos patches (global average pooling)
        x = x.mean(dim=1)

        return self.fc(x)                # (B, 1)
