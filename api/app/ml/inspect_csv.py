import pandas as pd
import os

# Caminho real do utilizador
BASE = r"D:\02_RO_\RO_TRADE\ML_Trade\api\data\history"

def inspect(symbol: str):
    # O downloader grava ASML_AS_1H.csv, ou seja, ponto vira underscore
    file_path = os.path.join(BASE, f"{symbol.replace('.', '_')}_1H.csv")
    print("→ Ficheiro:", file_path)

    if not os.path.exists(file_path):
        print("❌ Não encontrado.")
        return

    print("\n=== LER SEM NENHUMA CONVERSÃO (dtype=str) ===")
    df = pd.read_csv(file_path, dtype=str)
    print("\nColunas:", list(df.columns))
    print("\nPrimeiras 5 linhas:")
    print(df.head(5))

    print("\nÚltimas 5 linhas:")
    print(df.tail(5))

    print("\nTipos (tudo string):")
    print(df.dtypes)

    print("\n=== LER COM INDEX COL = 0 ===")
    try:
        df2 = pd.read_csv(file_path, index_col=0, dtype=str)
        print(df2.head(5))
        print("Index sample:", df2.index[:3])
    except Exception as e:
        print("Falhou index_col:", e)

    print("\n=== LER COM SENSOR DE DATETIME ===")
    try:
        df3 = pd.read_csv(file_path, index_col=0, parse_dates=True)
        print(df3.head(5))
        print("Index type:", type(df3.index[0]))
    except Exception as e:
        print("Falhou parse_dates:", e)


if __name__ == "__main__":
    inspect("ASML.AS")
