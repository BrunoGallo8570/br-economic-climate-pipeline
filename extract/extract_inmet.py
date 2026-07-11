import zipfile
import re
import pandas as pd
import duckdb
from pathlib import Path
from datetime import datetime

ZIP_PATH = "tmp_inmet/2023.zip"
DB_PATH = "data/pipeline.duckdb"

COLUMN_RENAME = {
    "Data": "data",
    "Hora UTC": "hora_utc",
    "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": "precipitacao_mm",
    "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)": "pressao_mb",
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)": "temperatura_c",
    "UMIDADE RELATIVA DO AR, HORARIA (%)": "umidade_pct",
    "VENTO, VELOCIDADE HORARIA (m/s)": "vento_ms",
}

def parse_station_file(f, filename):
    meta_lines = [f.readline().decode("latin-1") for _ in range(8)]
    metadata = {}
    for line in meta_lines:
        key, value = line.strip().split(";", 1)
        metadata[key.replace(":", "").strip()] = value

    df = pd.read_csv(
        f, sep=";", decimal=",", encoding="latin-1", skiprows=0
    )
    df = df.rename(columns=COLUMN_RENAME)
    keep_cols = list(COLUMN_RENAME.values())
    df = df[[c for c in keep_cols if c in df.columns]]

    df["estacao_codigo"] = metadata.get("CODIGO (WMO)")
    df["estacao_nome"] = metadata.get("ESTACAO")
    df["uf"] = metadata.get("UF")
    df["regiao"] = metadata.get("REGIAO")
    df["latitude"] = float(metadata.get("LATITUDE", "0").replace(",", "."))
    df["longitude"] = float(metadata.get("LONGITUDE", "0").replace(",", "."))
    df["altitude"] = float(metadata.get("ALTITUDE", "0").replace(",", "."))
    df["arquivo_origem"] = filename
    return df

def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("DROP TABLE IF EXISTS bronze.clima_raw")

    total_rows = 0
    first = True
    with zipfile.ZipFile(ZIP_PATH) as z:
        names = [n for n in z.namelist() if n.upper().endswith(".CSV")]
        print(f"{len(names)} estacoes encontradas no arquivo.")
        for i, name in enumerate(names, 1):
            with z.open(name) as f:
                df = parse_station_file(f, name)
            df["loaded_at"] = datetime.now()

            if first:
                con.execute("CREATE TABLE bronze.clima_raw AS SELECT * FROM df")
                first = False
            else:
                con.execute("INSERT INTO bronze.clima_raw SELECT * FROM df")

            total_rows += len(df)
            if i % 50 == 0:
                print(f"{i}/{len(names)} estacoes processadas...")

    print(f"Total: {total_rows} registros inseridos.")
    con.close()

if __name__ == "__main__":
    main()
