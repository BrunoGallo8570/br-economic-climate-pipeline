# Operational Documentation - BR Economic & Climate Pipeline

This document records what was built, the technical decisions made, and the reasoning behind each one. It complements the README (which focuses on "how to use") -- this document focuses on "what was done and why".

## Project goal

Personal portfolio project to practice and demonstrate, end to end, the lifecycle of a real data pipeline: extraction from a large public data source, layered transformation with quality tests, automated orchestration, version control and continuous integration.

## Timeline of what was built

1. Environment setup: Docker, Git, GitHub, VSCode
2. Extraction of hourly climate data from INMET (bronze layer) -- initially a single load of one year, later evolved into an incremental load (last complete year + current year)
3. Transformation with dbt: silver layer (staging, cleaning and typing) and gold layer (marts, daily aggregation per station)
4. Data quality tests (not_null, composite key uniqueness) and documentation/lineage generated via `dbt docs`
5. Orchestration with Apache Airflow via Docker, with a DAG connecting extraction -> dbt run -> dbt test
6. Extraction adjusted for incremental loading (avoids reprocessing historical data already loaded)
7. CI/CD pipeline on GitHub Actions (lint, dbt model validation, DAG import validation)
8. README and operational documentation (this document)

## Detailed stack: what each tool is, what it does, and why it was chosen

### DuckDB

**What it is**: an analytical (OLAP) database that runs embedded within the application's own process, with no need for a separate server -- similar to SQLite, but optimized for analytical queries (aggregations, group-by, joins over large volumes) rather than transactional workloads.

**What it does in this project**: stores all three data layers (bronze, silver, gold) in a single `.duckdb` file, and executes all of dbt's SQL transformations.

**Why it was chosen**: for a personal/portfolio project, spinning up a Spark cluster or a cloud data warehouse (BigQuery, Snowflake) would be unnecessary complexity and cost. DuckDB processes millions of rows (in our case, ~5-8 million) in seconds, running on a laptop, with no server, no cost, and no network connection required. It demonstrates that the right tool depends on the scale of the problem -- not every data pipeline needs distributed infrastructure.

**Important limitation learned in practice**: DuckDB allows only one write connection at a time to the same file. This caused "lock" errors when the VSCode DuckDB extension and dbt tried to access the database simultaneously -- a real-world lesson about concurrency in embedded databases.

### dbt (Data Build Tool) with the dbt-duckdb adapter

**What it is**: a data transformation tool that uses SQL and Jinja (templating) to define models, with a built-in framework for testing, documentation, and dependency management between tables.

**What it does in this project**: transforms raw data (bronze) into clean, typed data (silver/staging), then into analysis-ready aggregations (gold/marts). It also runs data quality tests and generates documentation with a lineage graph.

**Why it was chosen**: it is the industry standard for analytical transformation (used by companies of all sizes). Without dbt, these transformations could be done with standalone Python scripts, but we would lose: declarative data tests, automatic documentation, and automatic tracking of dependencies between tables (lineage). This is what turns a set of scripts into a governed data project.

### Apache Airflow

**What it is**: a workflow orchestration platform that allows pipelines to be defined as code (DAGs -- Directed Acyclic Graphs), with scheduling, failure monitoring, and automatic retry configuration.

**What it does in this project**: orchestrates the sequence extract_inmet -> dbt_run -> dbt_test, with a visual interface to track each run, view error logs, and trigger manual executions.

**Why it was chosen**: it is the most widely used orchestrator in the data engineering industry. Without it, the pipeline would depend on manually running scripts in sequence (which is how the project started) -- this does not scale, has no failure visibility, and keeps no execution history. Airflow also forced a real problem to be solved: the pipeline could not depend on files manually downloaded on the developer's machine -- it had to be 100% reproducible from scratch (this is what motivated the fix to the extraction script so it downloads data automatically).

### Docker and Docker Compose

**What it is**: containerization technology that packages an application and all of its dependencies (libraries, versions, minimal operating system) into an isolated, portable unit.

**What it does in this project**: runs Airflow and all of its supporting infrastructure (Postgres for metadata, Redis as a message queue) in isolated containers, orchestrated by Docker Compose from a single configuration file.

**Why it was chosen**: Airflow has several dependencies (metadata database, task queue, multiple processes: webserver, scheduler, worker) that would be complex to install and maintain directly on the operating system. Containerizing makes the environment reproducible on any machine (the same `docker-compose.yaml` brings up an identical project on another computer) and avoids the classic "works on my machine" problem.

**Recorded technical decision**: a custom Docker image was built (via `Dockerfile`) based on the official Airflow image, adding the Python libraries the pipeline needs (dbt, pandas, duckdb). This was necessary because the Airflow container does not include these libraries by default.

### Git and GitHub

**What it is**: Git is a distributed version control system; GitHub is a cloud-hosted platform for Git repositories, with additional collaboration features.

**What it does in this project**: versions all the code (scripts, DAGs, dbt models, configuration files), keeping a full history of changes, and hosts the repository publicly for portfolio purposes.

**Why it was chosen**: it is the industry standard for code versioning, essential both for team collaboration and for an individual portfolio -- a technical recruiter expects to find the code in a public, readable Git repository.

### GitHub Actions (CI/CD)

**What it is**: an automation tool built into GitHub that runs workflows (sequences of commands) automatically on repository events (such as a push or pull request).

**What it does in this project**: on every push, it automatically runs three checks: Python code linting (flake8), dbt model syntax and reference validation (`dbt parse`), and validation that the Airflow DAG can be imported without errors.

**Why it was chosen**: without CI, a syntax error or a broken reference in a dbt model would only be discovered when someone tried to run the pipeline manually -- possibly days later, and possibly in production. CI moves that detection to push time, before the error can propagate.

**Recorded technical decision**: CI does not run `dbt test` against real data, because the DuckDB database (holding production data) is not versioned in Git (large binary file, data is not code). CI uses a separate profile (`profiles.yml` inside the dbt project itself) pointing to an in-memory DuckDB database, validating only the structure and syntax of the models -- not the data itself.

## Real technical incidents and how they were resolved

Documenting real problems (not just the happy path) is part of good engineering documentation.

1. **INMET file encoding and format**: files in Latin-1 (not UTF-8), `;` as the field separator, comma as the decimal separator, and 8 metadata lines before the actual data header. Resolved with specific parsing (`encoding="latin-1"`, `decimal=","`, manual reading of metadata lines).

2. **Invalid data in production**: one INMET station returned the literal text value `"NULL"` in the altitude field, breaking the conversion to a number. Resolved with a safe conversion function (`safe_float`) that treats invalid values as null instead of failing.

3. **DuckDB file lock**: dbt and the VSCode DuckDB extension cannot write to the same `.duckdb` file at the same time. Resolved by adopting the practice of disconnecting the extension before running dbt/Python commands.

4. **Airflow worker crash loop**: a recent version of the `click` library (8.3.0), installed as a transitive dependency of dbt, broke the startup of Airflow's Celery worker. Resolved by pinning `click==8.2.1` in the Docker image's `requirements.txt`.

5. **GitHub Actions blocking workflow push**: the personal access token (PAT) used with Git did not have the `workflow` scope required to create/edit files inside `.github/workflows/`. Resolved by generating a new token with that additional scope.

6. **Pre-existing conflicting Airflow environment**: an old, unrelated Airflow installation existed on the same machine, occupying the default port 8080. Resolved by migrating the project to port 8081 and removing the old installation (which was an unused test).

