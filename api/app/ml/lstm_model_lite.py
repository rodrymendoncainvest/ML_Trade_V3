# lstm_model_lite.py

import torch
import torch.nn as nn


class LSTMLiteModel(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, num_classes=5, dropout=0.2):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout
        )

        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]      # usar a última saída da sequência
        out = self.fc(out)
        return out
