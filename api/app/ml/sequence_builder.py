# sequence_builder.py

import numpy as np
import torch

class SequenceBuilder:
    """
    Constrói janelas temporais fixas (seq_len = 50) para treinar a LSTM.
    """

    def __init__(self, seq_len=50):
        self.seq_len = seq_len

    def build_sequences(self, df, feature_cols, label_col):
        """
        df: dataframe final (já com labels e features normalizadas)
        feature_cols: lista das colunas de input
        label_col: nome da coluna da label
        """

        data = df.copy()
        values = data[feature_cols].values
        labels = data[label_col].values

        X, y = [], []

        # Criar janelas temporais
        for i in range(len(values) - self.seq_len):
            seq = values[i : i + self.seq_len]
            target = labels[i + self.seq_len]

            X.append(seq)
            y.append(target)

        # Converter para tensores PyTorch
        X = torch.tensor(np.array(X, dtype=np.float32))
        y = torch.tensor(np.array(y, dtype=np.int64))

        return X, y
