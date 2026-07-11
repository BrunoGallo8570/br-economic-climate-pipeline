select
    estacao_codigo,
    estacao_nome,
    uf,
    regiao,
    data_referencia,
    round(avg(temperatura_c), 2) as temperatura_media_c,
    round(max(temperatura_c), 2) as temperatura_maxima_c,
    round(min(temperatura_c), 2) as temperatura_minima_c,
    round(sum(precipitacao_mm), 2) as precipitacao_total_mm,
    round(avg(umidade_pct), 2) as umidade_media_pct,
    round(avg(vento_ms), 2) as vento_medio_ms,
    count(*) as horas_registradas
from {{ ref('stg_clima') }}
group by 1, 2, 3, 4, 5
