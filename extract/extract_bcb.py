import requests
import duckdb
from datetime import datetime

# Série 11 = Taxa Selic diária
URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados"
    "?formato=json&dataInicial=01/01/2024&dataFinal=31/12/2024"
)

def extract():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    return response.json()

def load(data):
    con = duckdb.connect("data/pipeline.duckdb")
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    con.execute("""
        CREATE TABLE IF NOT EXISTS bronze.selic_raw (
            data VARCHAR,
            valor VARCHAR,
            loaded_at TIMESTAMP
        )
    """)
    loaded_at = datetime.now()
    rows = [(d["data"], d["valor"], loaded_at) for d in data]
    con.executemany(
        "INSERT INTO bronze.selic_raw VALUES (?, ?, ?)", rows
    )
    print(f"{len(rows)} registros inseridos.")
    con.close()

if __name__ == "__main__":
    data = extract()
    load(data)
