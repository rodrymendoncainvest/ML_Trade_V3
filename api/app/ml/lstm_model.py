# lstm_model.py

import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, n_features, hidden_size=64, num_layers=2, num_classes=5):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=n_features,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2
        )

        self.fc = nn.Linear(hidden_size, num_classes)

    def forward(self, x):
        x, _ = self.lstm(x)
        x = x[:, -1, :]          # último timestep
        x = self.fc(x)
        return x
