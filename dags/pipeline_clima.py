from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

default_args = {
    "owner": "bruno",
    "retries": 1,
}

with DAG(
    dag_id="pipeline_clima_inmet",
    description="Pipeline de dados climaticos do INMET: extracao -> dbt run -> dbt test",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,  # por enquanto so manual, depois definimos frequencia
    catchup=False,
    tags=["clima", "inmet", "dbt"],
) as dag:

    extract = BashOperator(
        task_id="extract_inmet",
        bash_command="cd /opt/airflow && python3 extract/extract_inmet.py",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/airflow/dbt_project && dbt run --profiles-dir /opt/airflow/.dbt",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/airflow/dbt_project && dbt test --profiles-dir /opt/airflow/.dbt",
    )

    extract >> dbt_run >> dbt_test
