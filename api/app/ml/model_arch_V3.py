# model_arch_V3.py
# Arquitetura GRU + Attention + Multi-Head (direção + tendência) — V3

import torch
import torch.nn as nn
import torch.nn.functional as F


class AttentionLayer(nn.Module):
    """
    Atenção calibrada:
    - Normalize states before projection
    - Produz scores estáveis
    """

    def __init__(self, hidden_dim: int):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_dim)
        self.W = nn.Linear(hidden_dim, hidden_dim // 2, bias=False)
        self.v = nn.Linear(hidden_dim // 2, 1, bias=False)

    def forward(self, h):
        """
        h: (batch, seq_len, hidden_dim)
        """
        h_norm = self.norm(h)
        score = torch.tanh(self.W(h_norm))
        score = self.v(score).squeeze(-1)  # (B, T)
        attn = F.softmax(score, dim=1)
        context = torch.sum(h * attn.unsqueeze(-1), dim=1)
        return context, attn


class ModelV3(nn.Module):
    """
    Modelo GRU + Attention com duas heads:
      - direction_head: 2 classes (down/up)
      - trend_head: 3 classes (down/up/range)
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int = 64,
        num_layers: int = 2,
        dropout: float = 0.15,
    ):
        super().__init__()

        self.hidden_size = hidden_size

        # Encoder GRU bidirecional
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )

        self.ln_gru = nn.LayerNorm(hidden_size * 2)
        self.attn = AttentionLayer(hidden_dim=hidden_size * 2)

        # Main feature projection
        self.fc_main = nn.Linear(hidden_size * 2, hidden_size)
        self.ln_main = nn.LayerNorm(hidden_size)

        # Heads
        self.dir_head = nn.Linear(hidden_size, 2)   # direção
        self.trend_head = nn.Linear(hidden_size, 3) # tendência

        self.dropout = nn.Dropout(dropout)

    def forward(self, x):
        """
        x: (batch, seq_len, input_size)
        returns:
            dir_logits → (batch, 2)
            trend_logits → (batch, 3)
        """

        h, _ = self.gru(x)
        h = self.ln_gru(h)

        ctx, attn = self.attn(h)

        z = torch.relu(self.ln_main(self.fc_main(ctx)))
        z = self.dropout(z)

        dir_logits = self.dir_head(z)
        trend_logits = self.trend_head(z)

        return dir_logits, trend_logits
