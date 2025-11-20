# test_signal_lite.py

from ml.signal_engine_lite import SignalEngineLite


def main():
    print("=== TESTE SIGNAL ENGINE LITE ===")

    symbol = "ASML.AS"
    engine = SignalEngineLite(symbol)

    signal = engine.generate_signal(seq_len=50)

    print("\n=== RESULTADO DO SINAL ===")
    for k, v in signal.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
