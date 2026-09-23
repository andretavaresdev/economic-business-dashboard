# Painel de Cenário Econômico para Negócios

![Tests](https://github.com/andretavaresdev/economic-business-dashboard/actions/workflows/tests.yml/badge.svg)

Pipeline de dados que coleta indicadores econômicos da API do Banco Central do Brasil (SGS), armazena o histórico no PostgreSQL e apresenta um dashboard analítico em Streamlit — com métricas derivadas orientadas a negócio, não apenas os dados brutos.

## Arquitetura

```text
┌──────────────┐     ┌───────────────────────────────┐     ┌────────────┐     ┌───────────────┐
│  API do BCB  │────▶│  ETL (src/run_etl.py)          │────▶│ PostgreSQL │────▶│   Streamlit   │
│    (SGS)     │     │  extract → transform → load    │     │            │     │   (app.py)    │
└──────────────┘     │  + audit (execucoes_etl)       │     └─────┬──────┘     └───────▲───────┘
                      └───────────────────────────────┘           │                    │
                                                                    ▼                    │
                                                        ┌───────────────────┐            │
                                                        │  src/queries.py   │────────────┘
                                                        │  src/metrics.py   │
                                                        └───────────────────┘
```

| Camada | Módulo | Responsabilidade |
|---|---|---|
| Extração | `src/extract.py` | Consulta a API do SGS/BCB para um indicador e período. |
| Transformação | `src/transform.py` | Converte/valida os registros brutos em `IndicatorValue`. |
| Carga | `src/load.py` | Upsert de indicador e valores no PostgreSQL. |
| Auditoria | `src/audit.py` | Registra início/fim de cada execução do pipeline em `execucoes_etl`. |
| Orquestração | `src/run_etl.py` | CLI que decide a janela de datas (backfill x incremental) e roda o pipeline por indicador. |
| Consulta | `src/queries.py` | Leitura do PostgreSQL para o dashboard (valores mais recentes e histórico). |
| Métricas | `src/metrics.py` | Camada analítica: métricas derivadas a partir do histórico (ver abaixo). |
| Apresentação | `app.py` | Dashboard Streamlit: cartões, filtros, gráfico e tabela. |

## Estrutura do projeto

```text
.
├── app.py                      # Dashboard Streamlit
├── docker-compose.yml          # PostgreSQL local
├── pyproject.toml              # Configuração do ruff
├── pytest.ini                  # Configuração do pytest
├── requirements.txt            # Dependências de runtime
├── requirements-dev.txt        # + dependências de desenvolvimento (ruff)
├── sql/
│   ├── init.sql                # Schema inicial (roda uma vez, em volume novo)
│   └── migrations/             # Alterações de schema para bancos já existentes
├── src/
│   ├── audit.py
│   ├── config.py
│   ├── database.py
│   ├── extract.py
│   ├── indicators.py
│   ├── load.py
│   ├── metrics.py
│   ├── queries.py
│   ├── run_etl.py
│   └── transform.py
├── tests/                      # Um arquivo de teste por módulo em src/ e para app.py
└── .github/workflows/tests.yml # CI: lint (ruff) + testes (pytest)
```

## Indicadores

| Indicador | Código SGS | Unidade | Periodicidade | Janela de reprocessamento |
|---|---|---|---|---|
| Selic | 432 | % ao ano | Diária | 7 dias |
| IPCA | 433 | % ao mês | Mensal | 90 dias |
| Dólar comercial | 1 | R$/US$ | Diária | 7 dias |

A "janela de reprocessamento" é quantos dias antes da última data já armazenada o ETL refaz a carga a cada execução incremental, para absorver eventuais revisões da série pelo BCB.

## Métricas derivadas (`src/metrics.py`)

O dashboard não mostra só os valores brutos — calcula indicadores de negócio a partir do histórico:

- **IPCA acumulado em 12 meses** — juros compostos sobre as taxas mensais (`(1 + taxa/100)` multiplicado mês a mês, não somado), exigindo 12 meses consecutivos sem lacunas.
- **Mudança da Selic em pontos percentuais** — comparação com 12 meses atrás por padrão, já que a Selic só muda após decisões do Copom; uma janela curta costumaria mostrar variação zero mesmo com política monetária diferente.
- **Variação do dólar em 30 dias** — comparação percentual de 30 dias corridos; a consulta ao banco usa uma folga de 37 dias (`DOLLAR_VARIATION_HISTORY_BUFFER_DAYS`) só para garantir que exista um pregão anterior disponível mesmo se o dia exato cair num fim de semana ou feriado — a comparação em si continua sendo de 30 dias.
- **Comparação genérica entre valor atual e período anterior** (`compare_to_previous_period`) — usada na seção "Histórico" do dashboard, acompanhando o período selecionado pelo usuário na barra lateral.

## Pré-requisitos

- Python 3.12+
- Docker e Docker Compose (para o PostgreSQL local)

## Como rodar (do zero)

```bash
# 1. Clonar e entrar no projeto
git clone <url-do-repositorio>
cd economic-business-dashboard

# 2. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements-dev.txt

# 3. Variáveis de ambiente
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/Mac

# 4. Subir o PostgreSQL
docker compose up -d

# 5. Popular o histórico (5 anos) para os três indicadores
python -m src.run_etl --indicator all --backfill

# 6. Abrir o dashboard
streamlit run app.py
```

Depois da carga inicial, as próximas execuções do ETL são incrementais (sem `--backfill`) e só reprocessam a janela recente de cada indicador:

```bash
python -m src.run_etl --indicator all
```

## Migrações de banco

O `docker-compose.yml` monta `sql/init.sql` como script de inicialização do container Postgres — ele só roda **uma vez**, quando o volume de dados é criado pela primeira vez. Se o volume já existir (ex.: você já rodou `docker compose up` antes) e o schema mudar, alterações em `init.sql` **não são reaplicadas automaticamente**.

Para esses casos, mudanças de schema vão em `sql/migrations/` e são aplicadas manualmente contra o container em execução:

```bash
docker exec -i economic-business-postgres psql -U economic_user -d economic_dashboard < sql/migrations/001_add_indicator_code_to_etl_executions.sql
```

Para começar do zero (perde os dados locais), remova o volume: `docker compose down -v`.

## Testes

Todos os testes usam mocks/`monkeypatch` para a camada de banco — não é necessário ter o PostgreSQL rodando para testá-los.

```bash
pytest
```

## Qualidade de código

O projeto usa [ruff](https://docs.astral.sh/ruff/) como linter (imports não usados, nomes indefinidos, bugs comuns, ordenação de imports):

```bash
ruff check .
```

## Integração contínua

`.github/workflows/tests.yml` roda `ruff check .` e `pytest` a cada push/PR na branch `main`. O badge no topo deste README reflete o status da última execução em [andretavaresdev/economic-business-dashboard](https://github.com/andretavaresdev/economic-business-dashboard).

## Variáveis de ambiente

| Variável | Descrição | Exemplo |
|---|---|---|
| `POSTGRES_DB` | Nome do banco | `economic_dashboard` |
| `POSTGRES_USER` | Usuário do banco | `economic_user` |
| `POSTGRES_PASSWORD` | Senha do banco | `economic_password` |
| `POSTGRES_HOST` | Host do banco | `localhost` |
| `POSTGRES_PORT` | Porta do banco | `5433` |
