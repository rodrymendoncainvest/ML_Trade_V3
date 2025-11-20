from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd

from app.ml.engine_backtest import sweep_thresholds, optimize_threshold


def _parse_list_arg(raw: str) -> List[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def _parse_thresholds(raw: str) -> List[float]:
    """
    Converte '0.50:0.65:0.01' -> [0.50, 0.51, ..., 0.65].
    """
    t0, t1, step = [float(x) for x in raw.split(":")]
    arr = np.arange(t0, t1 + 1e-9, step)
    return [float(x) for x in arr]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backtest/Sweep em batch de modelos ML_TRADE para vários símbolos/timeframes."
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
        default=300,
        help="Número de barras a usar no backtest (default: 300).",
    )
    parser.add_argument(
        "--thresholds",
        type=str,
        default="0.50:0.65:0.01",
        help="Intervalo de thresholds no formato 'ini:fim:step', ex.: '0.50:0.65:0.01'.",
    )
    parser.add_argument(
        "--metric",
        type=str,
        default="expectancy",
        help="Métrica de seleção do threshold (ex.: 'expectancy', 'profit_factor', 'win_rate').",
    )
    parser.add_argument(
        "--fees-bps",
        dest="fees_bps",
        type=float,
        default=0.0,
        help="Fees em basis points (ex.: 5 = 0.05%%).",
    )
    parser.add_argument(
        "--slippage-bps",
        dest="slippage_bps",
        type=float,
        default=0.0,
        help="Slippage em basis points (ex.: 5 = 0.05%%).",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="backtests_out",
        help="Diretório onde gravar CSV agregados (default: 'backtests_out').",
    )

    args = parser.parse_args(argv)

    symbols = _parse_list_arg(args.symbols)
    tfs = _parse_list_arg(args.tfs)
    thr_list = _parse_thresholds(args.thresholds)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=== ML_TRADE :: BACKTEST_ALL ===")
    print(f"Symbols      : {symbols}")
    print(f"Timeframes   : {tfs}")
    print(f"Limit        : {args.limit}")
    print(f"Thresholds   : {args.thresholds} -> {len(thr_list)} valores")
    print(f"Métrica      : {args.metric}")
    print(f"Fees bps     : {args.fees_bps}")
    print(f"Slippage bps : {args.slippage_bps}")
    print(f"Out dir      : {out_dir}")
    print("-" * 80)

    rows_global: List[dict] = []

    for symbol in symbols:
        for tf in tfs:
            pair = f"{symbol}_{tf}"
            print(f"[SWEEP] {pair} ...", end=" ", flush=True)
            try:
                sw = sweep_thresholds(
                    symbol=symbol,
                    tf=tf,
                    limit=args.limit,
                    thresholds=thr_list,
                    metric=args.metric,
                    fees_bps=args.fees_bps,
                    slippage_bps=args.slippage_bps,
                )
                best_row = sw["best_row"]
                best_thr = float(best_row.get("threshold"))
                best_metric = float(best_row.get(args.metric, float("nan")))
                print(f"OK  best_thr={best_thr:.4f}  {args.metric}={best_metric:.4f}")

                # Guardar todas as linhas deste par com info extra
                for r in sw["rows"]:
                    row = dict(r)
                    row["symbol"] = symbol
                    row["tf"] = tf
                    rows_global.append(row)

                # Guardar CSV específico deste par
                df_pair = pd.DataFrame(sw["rows"])
                pair_csv = out_dir / f"sweep_{symbol}_{tf}.csv"
                df_pair.to_csv(pair_csv, index=False)
            except Exception as exc:
                print(f"FALHOU  ({exc})")

    # CSV global agregando todos os símbolos/tfs
    if rows_global:
        df_all = pd.DataFrame(rows_global)
        all_csv = out_dir / "sweep_all_symbols.csv"
        df_all.to_csv(all_csv, index=False)
        print("-" * 80)
        print(f"Tabela global gravada em: {all_csv}")
    else:
        print("-" * 80)
        print("Nenhum resultado de sweep foi agregado (tudo falhou?).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
