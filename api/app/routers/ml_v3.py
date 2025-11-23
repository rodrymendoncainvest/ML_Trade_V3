# ======================================================================
# ML_V3 ROUTER — PIPELINE COMPLETO (Download → Clean → FE → Dataset → Train → Predict → Backtest → Report)
# ======================================================================

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import traceback
import pandas as pd


# ---------------------------------------------------------
# IMPORTS DO PIPELINE V3
# ---------------------------------------------------------
from app.ml.data_downloader import download_1h
from app.ml.data_manager import DataManager
from app.ml.feature_engineer_V3 import FeatureEngineerV3
from app.ml.dataset_builder_V3 import DatasetBuilderV3
from app.ml.model_trainer_V3 import ModelTrainerV3
from app.ml.model_inference_V3 import ModelInferenceV3
from app.ml.signal_engine_V3 import SignalEngineV3
from app.ml.backtester_V3 import BacktesterV3
from app.ml.report_V3 import ReportV3

# ---------------------------------------------------------
# LOGGER (NOVO)
# ---------------------------------------------------------
from app.ml.logger_v3 import LoggerV3
log = LoggerV3()

router = APIRouter(prefix="/ml_v3", tags=["ML_V3"])


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

class TrainRequest(BaseModel):
    symbol: str


class PredictRequest(BaseModel):
    symbol: str
    risk_mode: str = "moderate"


class BacktestRequest(BaseModel):
    symbol: str
    risk_mode: str = "moderate"


class ReportRequest(BaseModel):
    symbol: str


# ---------------------------------------------------------
# SAFE WRAPPER
# ---------------------------------------------------------

def _safe(func, operation="unknown", symbol=""):
    try:
        return func()
    except Exception as e:
        msg = f"{operation.upper()} ERROR [{symbol}]: {str(e)}"
        log.write_error(msg)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------
# /train
# ---------------------------------------------------------
@router.post("/train")
def train_v3(req: TrainRequest):

    def run():
        symbol = req.symbol.upper()
        log.write("train", symbol, "Treino iniciado.")

        # 1) Download
        df_raw = download_1h(symbol)
        log.write("train", symbol, "Download concluído.")

        # 2) Clean
        dm = DataManager()
        df_clean = dm.clean(df_raw)
        log.write("train", symbol, "Clean concluído.")

        # 3) Feature Engineering
        fe = FeatureEngineerV3()
        df_fe = fe.transform(df_clean)
        log.write("train", symbol, "Feature Engineering concluído.")

        # 4) Dataset
        ds = DatasetBuilderV3()
        X, y_dir, y_trend, scaler, feature_cols = ds.build_dataset(df_fe)
        log.write("train", symbol, f"Dataset construído: X={X.shape}")

        # 5) Train
        trainer = ModelTrainerV3(symbol=symbol)
        model_path = trainer.train()
        log.write("train", symbol, f"Treino concluído. Modelo → {model_path}")

        return {
            "ok": True,
            "symbol": symbol,
            "model_path": model_path,
            "features": feature_cols,
        }

    return _safe(run, operation="train", symbol=req.symbol)


# ---------------------------------------------------------
# /predict
# ---------------------------------------------------------
@router.get("/predict")
def predict_v3(symbol: str, risk_mode: str = "moderate"):

    def run():
        symbol_u = symbol.upper()
        log.write("predict", symbol_u, f"Predict iniciado (risk={risk_mode}).")

        # raw → clean → fe
        df_raw = download_1h(symbol_u)
        dm = DataManager()
        fe = FeatureEngineerV3()

        df_clean = dm.clean(df_raw)
        df_fe = fe.transform(df_clean)

        infer = ModelInferenceV3(symbol_u)
        out = infer.predict(df_fe)

        se = SignalEngineV3(risk_mode=risk_mode)
        signal = se.generate_signal(out)

        log.write("predict", symbol_u, f"Sinal calculado: {signal['signal']}")

        return {
            "ok": True,
            "symbol": symbol_u,
            "risk_mode": risk_mode,
            "inference": out,
            "signal": signal,
        }

    return _safe(run, operation="predict", symbol=symbol)


# ---------------------------------------------------------
# /backtest
# ---------------------------------------------------------
@router.get("/backtest")
def backtest_v3(symbol: str, risk_mode: str = "moderate"):

    def run():
        symbol_u = symbol.upper()
        log.write("backtest", symbol_u, f"Backtest iniciado (risk={risk_mode}).")

        dm = DataManager()
        fe = FeatureEngineerV3()

        # download raw
        df_raw = download_1h(symbol_u)

        # FIX ESSENCIAL → grava clean no disco
        df_clean = dm.clean_symbol(symbol_u, tf="1H")

        # fe normal
        df_fe = fe.transform(df_clean)

        bt = BacktesterV3(symbol=symbol_u, risk_mode=risk_mode)
        result = bt.run()             # usa o clean no disco

        log.write("backtest", symbol_u, "Backtest concluído.")

        return {
            "ok": True,
            "symbol": symbol_u,
            "risk_mode": risk_mode,
            "results": result,
        }

    return _safe(run, operation="backtest", symbol=symbol)


# ---------------------------------------------------------
# /report
# ---------------------------------------------------------
@router.post("/report")
def report_v3(req: ReportRequest):

    def run():
        import os
        symbol_u = req.symbol.upper()
        log.write("report", symbol_u, "Gerando relatório...")

        rep = ReportV3(symbol_u)

        # caminho corrigido (sem mexer na lógica)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        df_clean_path = os.path.join(base_dir, "data", "clean", f"{symbol_u}_1H_clean.csv")

        if not os.path.exists(df_clean_path):
            raise FileNotFoundError(f"Clean data not found for report: {df_clean_path}")

        df = pd.read_csv(df_clean_path, index_col=0)
        df.index = pd.to_datetime(df.index)

        # relatório com backtest vazio (como já tinhas)
        result = rep.generate({"equity_curve": [], "trades": []}, df)

        log.write("report", symbol_u, "Relatório gerado.")

        return {
            "ok": True,
            "symbol": symbol_u,
            "report": result,
        }

    return _safe(run, operation="report", symbol=req.symbol)


# ---------------------------------------------------------
# /full_run
# ---------------------------------------------------------
@router.post("/full_run")
def full_run_v3(req: TrainRequest, risk_mode: str = "moderate"):

    def run():
        symbol = req.symbol.upper()
        log.write("train", symbol, "FULL_RUN iniciado.")

        # Download → Clean → FE → Dataset
        df_raw = download_1h(symbol)
        dm = DataManager()
        fe = FeatureEngineerV3()

        df_clean = dm.clean(df_raw)
        df_fe = fe.transform(df_clean)

        ds = DatasetBuilderV3()
        X, y_dir, y_trend, scaler, feature_cols = ds.build_dataset(df_fe)

        # Train
        trainer = ModelTrainerV3(symbol=symbol)
        model_path = trainer.train()

        # Predict
        infer = ModelInferenceV3(symbol)
        out = infer.predict(df_fe)

        se = SignalEngineV3(risk_mode=risk_mode)
        signal = se.generate_signal(out)

        # Backtest
        bt = BacktesterV3(symbol=symbol, risk_mode=risk_mode)
        backtest = bt.run()

        # Report
        rep = ReportV3(symbol)
        report = rep.generate(backtest, df_clean)

        log.write("train", symbol, "FULL_RUN concluído.")

        return {
            "ok": True,
            "symbol": symbol,
            "model_path": model_path,
            "snapshot": out,
            "signal": signal,
            "backtest": backtest,
            "report": report,
        }

    return _safe(run, operation="full_run", symbol=req.symbol)
