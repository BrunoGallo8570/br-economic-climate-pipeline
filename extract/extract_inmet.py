import zipfile
import os
import requests
import pandas as pd
import duckdb
from datetime import datetime

DB_PATH = "data/pipeline.duckdb"
TMP_DIR = "tmp_inmet"

CURRENT_YEAR = datetime.now().year
LAST_COMPLETE_YEAR = CURRENT_YEAR - 1
YEARS_TO_PROCESS = [LAST_COMPLETE_YEAR, CURRENT_YEAR]

COLUMN_RENAME = {
    "Data": "data",
    "Hora UTC": "hora_utc",
    "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)": "precipitacao_mm",
    "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)": "pressao_mb",
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)": "temperatura_c",
    "UMIDADE RELATIVA DO AR, HORARIA (%)": "umidade_pct",
    "VENTO, VELOCIDADE HORARIA (m/s)": "vento_ms",
}


def zip_path_for(year):
    return f"{TMP_DIR}/{year}.zip"


def download_zip(year):
    os.makedirs(TMP_DIR, exist_ok=True)
    path = zip_path_for(year)
    url = f"https://portal.inmet.gov.br/uploads/dadoshistoricos/{year}.zip"
    print(f"Baixando {url} ...")
    headers = {"User-Agent": "Mozilla/5.0"}
    with requests.get(url, headers=headers, stream=True) as r:
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"Download de {year} concluido.")


def parse_station_file(f, filename, ano_referencia):
    meta_lines = [f.readline().decode("latin-1") for _ in range(8)]
    metadata = {}
    for line in meta_lines:
        key, value = line.strip().split(";", 1)
        metadata[key.replace(":", "").strip()] = value

    df = pd.read_csv(f, sep=";", decimal=",", encoding="latin-1", skiprows=0)
    df = df.rename(columns=COLUMN_RENAME)
    keep_cols = list(COLUMN_RENAME.values())
    df = df[[c for c in keep_cols if c in df.columns]]

    def safe_float(value):
        if value is None:
            return None
        value = value.strip()
        if value == "" or value.upper() == "NULL":
            return None
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None

    df["estacao_codigo"] = metadata.get("CODIGO (WMO)")
    df["estacao_nome"] = metadata.get("ESTACAO")
    df["uf"] = metadata.get("UF")
    df["regiao"] = metadata.get("REGIAO")
    df["latitude"] = safe_float(metadata.get("LATITUDE"))
    df["longitude"] = safe_float(metadata.get("LONGITUDE"))
    df["altitude"] = safe_float(metadata.get("ALTITUDE"))
    df["arquivo_origem"] = filename
    df["ano_referencia"] = ano_referencia
    return df


def load_year(con, year, first_ever):
    path = zip_path_for(year)
    if not os.path.exists(path):
        download_zip(year)

    total_rows = 0
    first_chunk = True
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.upper().endswith(".CSV")]
        print(f"[{year}] {len(names)} estacoes encontradas.")
        for i, name in enumerate(names, 1):
            with z.open(name) as f:
                df = parse_station_file(f, name, year)
            df["loaded_at"] = datetime.now()

            if first_ever and first_chunk:
                con.execute("CREATE TABLE bronze.clima_raw AS SELECT * FROM df")
                first_chunk = False
            else:
                con.execute("INSERT INTO bronze.clima_raw SELECT * FROM df")

            total_rows += len(df)
            if i % 100 == 0:
                print(f"[{year}] {i}/{len(names)} estacoes processadas...")

    print(f"[{year}] Total inserido: {total_rows} registros.")


def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")

    table_exists = con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_schema='bronze' AND table_name='clima_raw'"
    ).fetchone()[0] > 0

    if not table_exists:
        print("Tabela bronze.clima_raw nao existe. Carga inicial completa.")
        for year in YEARS_TO_PROCESS:
            load_year(con, year, first_ever=(year == YEARS_TO_PROCESS[0]))
    else:
        existing_years = [
            r[0] for r in con.execute(
                "SELECT DISTINCT ano_referencia FROM bronze.clima_raw"
            ).fetchall()
        ]
        print(f"Anos ja carregados: {existing_years}")

        for year in YEARS_TO_PROCESS:
            if year == CURRENT_YEAR:
                print(f"Ano corrente ({year}): removendo dados antigos e recarregando.")
                con.execute(
                    "DELETE FROM bronze.clima_raw WHERE ano_referencia = ?", [year]
                )
                # Sempre baixa de novo o ano corrente, pois o INMET atualiza mensalmente
                path = zip_path_for(year)
                if os.path.exists(path):
                    os.remove(path)
                load_year(con, year, first_ever=False)
            elif year not in existing_years:
                print(f"Ano {year} ainda nao carregado. Processando pela primeira vez.")
                load_year(con, year, first_ever=False)
            else:
                print(f"Ano {year} ja carregado e completo. Pulando (incremental).")

    con.close()


if __name__ == "__main__":
    main()
