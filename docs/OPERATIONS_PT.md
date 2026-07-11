# Documentacao Operacional - BR Economic & Climate Pipeline

Este documento registra o que foi construido, as decisoes tecnicas tomadas e o raciocinio por tras de cada uma delas. E um complemento ao README (que foca em "como usar") -- aqui o foco e "o que foi feito e por que".

## Objetivo do projeto

Projeto pessoal de portfolio para praticar e demonstrar, de ponta a ponta, o ciclo de vida de um pipeline de dados real: extracao de uma fonte publica de grande volume, transformacao em camadas com testes de qualidade, orquestracao automatizada, versionamento e integracao continua.

## Linha do tempo do que foi construido

1. Configuracao do ambiente: Docker, Git, GitHub, VSCode
2. Extracao de dados climaticos horarios do INMET (camada bronze) -- inicialmente carga unica de um ano, depois evoluida para carga incremental (ano completo + ano corrente)
3. Transformacao com dbt: camada silver (staging, limpeza e tipagem) e camada gold (marts, agregacao diaria por estacao)
4. Testes de qualidade de dados (not_null, unicidade de chave composta) e documentacao/linhagem gerada via `dbt docs`
5. Orquestracao com Apache Airflow via Docker, com uma DAG conectando extracao -> dbt run -> dbt test
6. Ajuste da extracao para carga incremental (evita reprocessar dados historicos ja carregados)
7. Pipeline de CI/CD no GitHub Actions (lint, validacao dos modelos dbt, validacao de importacao da DAG)
8. README e documentacao operacional (este documento)

## Stack detalhada: o que e cada ferramenta, o que ela faz e por que foi escolhida

### DuckDB

**O que e**: um banco de dados analitico (OLAP) que roda embutido no proprio processo da aplicacao, sem precisar de um servidor separado -- parecido com o SQLite, mas otimizado para consultas analiticas (agregacoes, groupby, joins em grandes volumes) em vez de transacoes.

**O que faz no projeto**: armazena as tres camadas de dados (bronze, silver, gold) em um unico arquivo `.duckdb`, e executa todas as transformacoes SQL do dbt.

**Por que foi escolhido**: para um projeto pessoal/portfolio, subir um cluster Spark ou um data warehouse na nuvem (BigQuery, Snowflake) seria complexidade e custo desnecessarios. O DuckDB processa milhoes de linhas (no nosso caso, ~5-8 milhoes) em segundos, rodando no proprio notebook, sem servidor, sem custo, e sem conexao de rede. Ele demonstra que a ferramenta certa depende da escala do problema -- nem todo pipeline de dados precisa de infraestrutura distribuida.

**Limitacao importante aprendida na pratica**: DuckDB permite apenas uma conexao de escrita por vez no mesmo arquivo. Isso gerou erros de "lock" quando a extensao do VSCode e o dbt tentavam acessar o banco simultaneamente -- uma licao real sobre concorrencia em bancos embutidos.

### dbt (Data Build Tool) com adapter dbt-duckdb

**O que e**: uma ferramenta de transformacao de dados que usa SQL e Jinja (templates) para definir modelos, com um framework embutido de testes, documentacao e controle de dependencias entre tabelas.

**O que faz no projeto**: transforma os dados brutos (bronze) em dados limpos e tipados (silver/staging) e depois em agregacoes prontas para analise (gold/marts). Tambem roda os testes de qualidade de dados e gera a documentacao com o grafo de linhagem.

**Por que foi escolhido**: e o padrao de mercado para transformacao analitica (usado por empresas de todos os tamanhos). Sem o dbt, essas transformacoes poderiam ser feitas com scripts Python soltos, mas perderiamos: testes de dados declarativos, documentacao automatica, e o rastreamento automatico de dependencias entre tabelas (linhagem). Isso e o que transforma um conjunto de scripts em um projeto de dados governado.

### Apache Airflow

**O que e**: uma plataforma de orquestracao de workflows, que permite definir pipelines como codigo (DAGs -- Directed Acyclic Graphs), agendar execucoes, monitorar falhas e configurar retentativas automaticas.

**O que faz no projeto**: orquestra a sequencia extract_inmet -> dbt_run -> dbt_test, com uma interface visual para acompanhar cada execucao, ver logs de erro e disparar execucoes manuais.

**Por que foi escolhido**: e o orquestrador mais usado no mercado de engenharia de dados. Sem ele, o pipeline dependeria de execucao manual dos scripts em sequencia (o que fizemos no inicio do projeto) -- o que nao escala, nao tem visibilidade de falhas, e nao tem historico de execucoes. O Airflow tambem obrigou a resolver um problema real: o pipeline nao podia depender de arquivos baixados manualmente na maquina do desenvolvedor -- teve que ser 100% reprodutivel a partir do zero (foi o que motivou a correcao do script de extracao para baixar os dados automaticamente).

### Docker e Docker Compose

**O que e**: tecnologia de containerizacao, que empacota uma aplicacao e todas as suas dependencias (bibliotecas, versoes, sistema operacional minimo) em uma unidade isolada e portavel.

**O que faz no projeto**: roda o Airflow e toda a sua infraestrutura de apoio (Postgres para metadados, Redis como fila de mensagens) em containers isolados, orquestrados pelo Docker Compose a partir de um unico arquivo de configuracao.

**Por que foi escolhido**: o Airflow tem varias dependencias (banco de metadados, fila de tarefas, multiplos processos: webserver, scheduler, worker) que seriam complexas de instalar e manter diretamente no sistema operacional. Containerizar torna o ambiente reproduzivel em qualquer maquina (o mesmo `docker-compose.yaml` sobe o projeto identico em outro computador) e evita o classico problema de "funciona na minha maquina".

**Decisao tecnica registrada**: construimos uma imagem Docker customizada (via `Dockerfile`) a partir da imagem oficial do Airflow, adicionando as bibliotecas Python que o pipeline precisa (dbt, pandas, duckdb). Isso foi necessario porque o container do Airflow, por padrao, nao tem essas bibliotecas instaladas.

### Git e GitHub

**O que e**: Git e um sistema de controle de versao distribuido; GitHub e uma plataforma de hospedagem de repositorios Git na nuvem, com recursos adicionais de colaboracao.

**O que faz no projeto**: versiona todo o codigo (scripts, DAGs, modelos dbt, configuracoes), mantendo historico completo de mudancas, e hospeda o repositorio publicamente para fins de portfolio.

**Por que foi escolhido**: e o padrao de mercado para versionamento de codigo, essencial tanto para trabalho em equipe quanto para portfolio individual -- um recrutador tecnico espera encontrar o codigo em um repositorio Git publico e legivel.

### GitHub Actions (CI/CD)

**O que e**: uma ferramenta de automacao integrada ao GitHub, que executa workflows (sequencias de comandos) automaticamente a cada evento no repositorio (como um push ou pull request).

**O que faz no projeto**: a cada push, roda automaticamente tres validacoes: lint do codigo Python (flake8), validacao de sintaxe e referencias dos modelos dbt (`dbt parse`), e validacao de que a DAG do Airflow consegue ser importada sem erros.

**Por que foi escolhido**: sem CI, um erro de sintaxe ou uma referencia quebrada em um modelo dbt so seria descoberto quando alguem tentasse rodar o pipeline manualmente -- possivelmente dias depois, e possivelmente em producao. O CI move essa deteccao para o momento do push, antes do erro se propagar.

**Decisao tecnica registrada**: o CI nao roda `dbt test` contra os dados reais, porque o banco DuckDB (com os dados de producao) nao e versionado no Git (arquivo binario grande, dados nao sao codigo). O CI usa um profile separado (`profiles.yml` dentro do proprio projeto dbt) apontando para um banco DuckDB em memoria, validando apenas a estrutura e sintaxe dos modelos -- nao os dados em si.

## Incidentes tecnicos reais e como foram resolvidos

Registrar problemas reais (e nao so o caminho feliz) e parte de uma boa documentacao de engenharia.

1. **Encoding e formato dos arquivos do INMET**: arquivos em Latin-1 (nao UTF-8), separador `;`, decimal com virgula, e 8 linhas de metadados antes do cabecalho real dos dados. Resolvido com parsing especifico (`encoding="latin-1"`, `decimal=","`, leitura manual das linhas de metadados).

2. **Dado invalido em producao**: uma estacao do INMET trouxe o valor literal `"NULL"` como texto no campo de altitude, quebrando a conversao para numero. Resolvido com uma funcao de conversao segura (`safe_float`) que trata valores invalidos como nulos em vez de falhar.

3. **Lock de arquivo do DuckDB**: o dbt e a extensao DuckDB do VSCode nao podem escrever no mesmo arquivo `.duckdb` simultaneamente. Resolvido adotando a pratica de desconectar a extensao antes de rodar comandos dbt/Python.

4. **Worker do Airflow em crash loop**: uma versao recente da biblioteca `click` (8.3.0), instalada como dependencia transitiva do dbt, quebrou a inicializacao do Celery worker do Airflow. Resolvido fixando a versao `click==8.2.1` no `requirements.txt` da imagem Docker.

5. **GitHub Actions bloqueando push de workflow**: o token de acesso pessoal (PAT) usado no Git nao tinha o escopo `workflow`, necessario para criar/editar arquivos dentro de `.github/workflows/`. Resolvido gerando um novo token com esse escopo adicional.

6. **Ambiente Airflow pre-existente conflitando**: havia uma instalacao antiga e nao relacionada do Airflow na mesma maquina, ocupando a porta padrao 8080. Resolvido migrando o projeto para a porta 8081 e removendo a instalacao antiga (que era apenas um teste sem uso).

