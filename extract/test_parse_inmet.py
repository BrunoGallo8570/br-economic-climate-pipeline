import pandas as pd

path = "tmp_inmet/INMET_CO_DF_A001_BRASILIA_01-01-2023_A_31-12-2023.CSV"

# Lê metadados (8 primeiras linhas)
with open(path, encoding="latin-1") as f:
    meta_lines = [next(f) for _ in range(8)]

metadata = {}
for line in meta_lines:
    key, value = line.strip().split(";", 1)
    metadata[key.replace(":", "")] = value

print("METADADOS:", metadata)

# Lê os dados (pula as 8 linhas de metadados)
df = pd.read_csv(
    path,
    sep=";",
    decimal=",",
    encoding="latin-1",
    skiprows=8,
)
print(df.shape)
print(df.head())
