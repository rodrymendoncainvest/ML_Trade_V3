# ============================================================
# ML_V3 — SSE PIPELINE COMPLETO (Download → Clean → FE → Dataset → Train → Predict → Backtest → Report)
# ============================================================

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
import time
import threading
import os
import pandas as pd
import numpy as np

# Pipeline V3 original — NÃO ALTERADOS
from app.ml.data_downloader import download_1h
from app.ml.data_manager import DataManager
from app.ml.feature_engineer_V3 import FeatureEngineerV3
from app.ml.dataset_builder_V3 import DatasetBuilderV3
from app.ml.model_trainer_V3 import ModelTrainerV3
from app.ml.model_inference_V3 import ModelInferenceV3
from app.ml.signal_engine_V3 import SignalEngineV3
from app.ml.backtester_V3 import BacktesterV3
from app.ml.report_V3 import ReportV3


router = APIRouter(prefix="/ml_v3", tags=["ML_V3_SSE"])


# ============================================================
# SERIALIZAÇÃO SEGURA PARA JSON (resolve Timestamp / numpy)
# ============================================================

def safe_json(obj):
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [safe_json(x) for x in obj]
    return obj


def ev(data: dict):
    safe = safe_json(data)
    return f"data: {json.dumps(safe)}\n\n"


# ============================================================
# /full_run_sse — Pipeline total com progresso SSE
# ============================================================
@router.get("/full_run_sse")
async def full_run_sse(symbol: str):

    def stream():
        q = []  # fila de eventos SSE

        # emitir evento SSE
        def emit(pct, msg):
            q.append({"progress": int(pct), "message": msg})

        # thread → pipeline
        def background():
            try:
                dm = DataManager()

                # ============================================================
                # 1) DOWNLOAD RAW
                # ============================================================
                emit(2, "A descarregar dados...")
                df_raw = download_1h(symbol)

                # ============================================================
                # 2) CLEAN + SAVE CLEAN
                # ============================================================
                emit(8, "A limpar e guardar dados limpos...")
                df_clean = dm.clean_symbol(symbol, tf="1H")

                # ============================================================
                # 3) RECARREGAR CLEAN DO DISCO
                # ============================================================
                file_clean = os.path.join(dm.CLEAN_DIR, f"{symbol}_1H_clean.csv")

                if not os.path.exists(file_clean):
                    raise FileNotFoundError(f"Clean file not created: {file_clean}")

                df_clean = pd.read_csv(file_clean, index_col=0)
                df_clean.index = pd.to_datetime(df_clean.index, utc=True)

                # ============================================================
                # 4) FEATURE ENGINEERING
                # ============================================================
                emit(20, "A criar features...")
                fe = FeatureEngineerV3()
                df_fe = fe.transform(df_clean)

                # ============================================================
                # 5) DATASET BUILDER
                # ============================================================
                emit(25, "A construir dataset...")
                ds = DatasetBuilderV3()
                X, y_dir, y_trend, scaler, feature_cols = ds.build_dataset(df_fe)

                # ============================================================
                # 6) TREINO
                # ============================================================
                trainer = ModelTrainerV3(symbol)
                trainer.set_sse_callback(emit)

                emit(30, "A iniciar treino do modelo...")
                model_path = trainer.train()

                # ============================================================
                # 7) PREDICT
                # ============================================================
                emit(90, "A prever com o modelo...")
                infer = ModelInferenceV3(symbol)
                pred_out = infer.predict(df_fe)

                # ============================================================
                # 8) SIGNAL ENGINE
                # ============================================================
                emit(93, "A gerar sinal final...")
                se = SignalEngineV3()
                signal = se.generate_signal(pred_out)

                # ============================================================
                # 9) BACKTEST
                # ============================================================
                emit(96, "A executar backtest...")
                bt = BacktesterV3(symbol)
                backtest = bt.run()   # <-- correto

                # ============================================================
                # 10) REPORT
                # ============================================================
                emit(98, "A gerar relatório final...")
                rep = ReportV3(symbol)
                report = rep.generate(backtest, df_clean)

                # ============================================================
                # DONE
                # ============================================================
                emit(100, "Pipeline concluído.")

                q.append({
                    "done": True,
                    "model_path": model_path,
                    "signal": signal,
                    "prediction": pred_out,
                    "backtest": backtest,
                    "report": report,
                })

            except Exception as e:
                q.append({"error": str(e)})
                q.append({"progress": 100, "message": "Erro fatal."})

        # Iniciar thread
        t = threading.Thread(target=background)
        t.start()

        # Emitir SSE
        while t.is_alive() or q:
            while q:
                yield ev(q.pop(0))
            time.sleep(0.15)

    return StreamingResponse(stream(), media_type="text/event-stream")
