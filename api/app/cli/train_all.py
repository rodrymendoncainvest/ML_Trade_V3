from __future__ import annotations

import argparse
import sys
from typing import List

from app.ml.engine_train import train_model


def _parse_list_arg(raw: str) -> List[str]:
    """
    Converte string 'AAPL,MSFT,GOOG' -> ['AAPL', 'MSFT', 'GOOG'].
    Ignora espaços.
    """
    return [x.strip() for x in raw.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Treino em batch de modelos ML_TRADE para vários símbolos/timeframes."
    )
    parser.add_argument(
        "--symbols",
        type=str,
        required=True,
        help="Lista de símbolos separada por vírgulas, ex.: 'AAPL,MSFT,GOOG'.",
    )
    parser.add_argument(
        "--tfs",
        type=str,
        default="1d",
        help="Lista de timeframes separada por vírgulas, ex.: '1d,1h'. Default: '1d'.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1200,
        help="Número máximo de barras a carregar para treino (default: 1200).",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=0.002,
        help="Zona morta para labels (ex.: 0.002 = 0.2%%). Default: 0.002.",
    )

    args = parser.parse_args(argv)

    symbols = _parse_list_arg(args.symbols)
    tfs = _parse_list_arg(args.tfs)

    if not symbols:
        print("ERRO: sem símbolos válidos em --symbols", file=sys.stderr)
        return 1
    if not tfs:
        print("ERRO: sem timeframes válidos em --tfs", file=sys.stderr)
        return 1

    print("=== ML_TRADE :: TRAIN_ALL ===")
    print(f"Symbols   : {symbols}")
    print(f"Timeframes: {tfs}")
    print(f"Limit     : {args.limit}")
    print(f"Eps       : {args.eps}")
    print("-" * 60)

    n_ok = 0
    n_err = 0

    for symbol in symbols:
        for tf in tfs:
            pair = f"{symbol}_{tf}"
            print(f"[TRAIN] {pair} ...", end=" ", flush=True)
            try:
                res = train_model(symbol=symbol, tf=tf, limit=args.limit, eps=args.eps)
                ok = bool(res.get("ok", True))
                key = res.get("key", f"{symbol.upper()}_{tf}")
                meta = res.get("meta", {}) or {}
                model_name = meta.get("metrics", {}).get("model", "?")
                cv_acc = meta.get("metrics", {}).get("cv_acc_mean", None)

                if ok:
                    n_ok += 1
                    extra = ""
                    if cv_acc is not None:
                        extra = f" | cv_acc_mean={cv_acc:.4f}"
                    print(f"OK  key={key} model={model_name}{extra}")
                else:
                    n_err += 1
                    detail = res.get("detail") or "desconhecido"
                    print(f"FALHOU  ({detail})")
            except Exception as exc:
                n_err += 1
                print(f"FALHOU  ({exc})")

    print("-" * 60)
    print(f"Concluído. Sucessos: {n_ok}  Falhas: {n_err}")
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
