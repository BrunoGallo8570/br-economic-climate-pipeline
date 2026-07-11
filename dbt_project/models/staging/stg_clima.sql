select
    estacao_codigo,
    estacao_nome,
    uf,
    regiao,
    latitude,
    longitude,
    altitude,
    strptime(data, '%Y/%m/%d')::date as data_referencia,
    cast(replace(hora_utc, ' UTC', '') as integer) as hora_utc,
    precipitacao_mm,
    pressao_mb,
    temperatura_c,
    umidade_pct,
    vento_ms,
    loaded_at
from {{ source('bronze', 'clima_raw') }}
