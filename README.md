# BR Economic & Climate Pipeline

Pipeline de engenharia de dados que extrai, transforma e disponibiliza dados climaticos historicos do Brasil (INMET), com arquitetura em camadas (bronze/silver/gold), testes de qualidade de dados e orquestracao via Airflow -- tudo containerizado com Docker.

Projeto pessoal de portfolio, construido para praticar e demonstrar competencias reais de engenharia de dados: extracao de dados publicos em larga escala, transformacao com dbt, orquestracao com Airflow, versionamento e CI/CD.

## Sobre os dados

Fonte: [INMET - Instituto Nacional de Meteorologia](https://portal.inmet.gov.br/dadoshistoricos), dados horarios de mais de 500 estacoes meteorologicas automaticas espalhadas pelo Brasil.

- Volume: ~5 milhoes de registros por ano processado
- Estrategia de carga: incremental -- ano completo mais recente e carregado uma unica vez; ano corrente e atualizado a cada execucao (comportamento real de producao)
- Granularidade original: horaria -> agregada para resumos diarios na camada gold

## Arquitetura

Pipeline em camadas (medallion architecture):

    INMET (API/ZIP) --> Bronze (raw) --> Silver (staging) --> Gold (marts)
                         DuckDB          dbt models          dbt models

- Bronze: dados brutos, uma linha por estacao/hora, sem transformacao
- Silver (staging): dados limpos, tipados corretamente, nomes de coluna padronizados
- Gold (marts): agregacoes diarias por estacao, prontas para analise (temperatura media/max/min, precipitacao total, umidade, vento)

Toda a orquestracao (extracao -> dbt run -> dbt test) e feita por uma DAG no Airflow, rodando em containers Docker.

## Stack e por que cada ferramenta foi escolhida

| Ferramenta | Papel no projeto | Por que essa escolha |
|---|---|---|
| DuckDB | Banco de dados analitico | Processa milhoes de linhas localmente, sem precisar de cluster (Spark) ou servidor de banco separado. Ideal para portfolio e para cargas de trabalho analiticas de porte pequeno/medio. |
| dbt (dbt-duckdb) | Transformacao (silver/gold) | Traz testes de dados, documentacao automatica e linhagem (lineage) versionados como codigo -- e o padrao de mercado para transformacao analitica. |
| Apache Airflow | Orquestracao | Agenda e monitora a execucao do pipeline, com retries automaticos, logs centralizados e visualizacao do fluxo -- padrao de mercado para orquestracao de dados. |
| Docker / Docker Compose | Containerizacao | Isola o ambiente do Airflow (e suas dependencias: Postgres, Redis) do sistema operacional, tornando o projeto reproduzivel em qualquer maquina. |
| Git / GitHub | Versionamento | Historico de mudancas, colaboracao e portfolio publico do codigo. |
| GitHub Actions | CI/CD | Valida automaticamente a cada push: lint do codigo Python, sintaxe e referencias dos modelos dbt, e importacao correta da DAG do Airflow. |

## Como rodar o projeto

Pre-requisitos: Docker e Docker Compose instalados.

1. Clonar o repositorio
2. Criar o ambiente Python local (usado para rodar dbt e scripts fora do Airflow, se desejar):

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements-dev.txt

3. Subir o Airflow via Docker:

    mkdir -p ./logs ./plugins ./config
    echo -e "AIRFLOW_UID=$(id -u)" > .env
    docker compose up airflow-init
    docker compose up -d

4. Acessar o Airflow em http://localhost:8081 (credenciais definidas na configuracao local, nao versionadas)
5. Disparar manualmente a DAG `pipeline_clima_inmet`

## Estrutura do projeto

    .
    |-- dags/                  DAG do Airflow
    |-- dbt_project/           Modelos, testes e documentacao dbt
    |   |-- models/staging/    Camada silver
    |   `-- models/marts/      Camada gold
    |-- extract/               Scripts de extracao (Python)
    |-- data/                  Banco DuckDB local (nao versionado)
    |-- .github/workflows/     Pipeline de CI
    |-- Dockerfile             Imagem customizada do Airflow (com dbt/pandas/duckdb)
    `-- docker-compose.yaml    Orquestracao dos containers (Airflow, Postgres, Redis)

## Governanca de dados

- Testes automatizados (dbt): not_null, unicidade de chave composta (estacao + data)
- Documentacao de colunas e linhagem gerada automaticamente (`dbt docs generate`)
- CI/CD: todo push valida lint do codigo, sintaxe dos modelos dbt e importacao da DAG
- Estrategia de carga incremental documentada e auditavel (coluna `loaded_at` em todas as tabelas)
