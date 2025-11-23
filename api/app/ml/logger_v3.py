# ============================================================
# LOGGER V3 — logs humanos, diários, por operação
# ============================================================

import os
from datetime import datetime

class LoggerV3:

    def __init__(self):
        # ROOT = api/
        self.ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.LOG_DIR = os.path.join(self.ROOT, "data", "logs")
        os.makedirs(self.LOG_DIR, exist_ok=True)

    # -------------------------------------------------------
    # Caminho final do log para a operação
    # -------------------------------------------------------
    def _file(self, operation: str, symbol: str):
        day = datetime.utcnow().strftime("%Y%m%d")
        filename = f"{operation}_{symbol}_{day}.log"
        return os.path.join(self.LOG_DIR, filename)

    # -------------------------------------------------------
    # Linha formatada
    # -------------------------------------------------------
    def _line(self, text: str):
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return f"[{stamp}] {text}\n"

    # -------------------------------------------------------
    # Escrever log
    # -------------------------------------------------------
    def write(self, operation: str, symbol: str, text: str):
        path = self._file(operation, symbol)
        with open(path, "a", encoding="utf-8") as f:
            f.write(self._line(text))
        return path

    # -------------------------------------------------------
    # Atalho para erros globais
    # -------------------------------------------------------
    def write_error(self, text: str):
        day = datetime.utcnow().strftime("%Y%m%d")
        path = os.path.join(self.LOG_DIR, f"errors_{day}.log")
        with open(path, "a", encoding="utf-8") as f:
            f.write(self._line(text))
        return path
