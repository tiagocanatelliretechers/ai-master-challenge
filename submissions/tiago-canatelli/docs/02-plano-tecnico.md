# 02 · Plano Técnico — RavenStack Churn Lake

> Como o [plano de projeto](01-plano-projeto.md) vira sistema. Documento vivo, iniciado em 2026-10-23.

---

## 1. Visão geral

```
                ┌──────────────────────── Supabase (Postgres 17 + Storage + Realtime) ────────────────────────────┐
 Kaggle CSVs    │                                                                                                   │
 (5 arquivos)──►│  Storage bucket `raw/`  ──►  bronze.*  ──►  silver.*  ──►  gold.*  ──►  api.* (views/RPC só leitura)│
     ▲          │   (landing imutável)       (1:1 CSV)     (tipado,      (KPIs,          │                          │
     │          │                                          DQ, FKs)      account_360,    │                          │
  pipeline      │   ops.ingestion_runs · ops.ingestion_steps · ops.dq_results · ops.catalog                         │
  Python  ─────►│   app.prompt_templates · app.prompt_versions · app.ai_runs                                        │
  (CLI)         │                                                                                                   │
                └───────────────────────────────────────────────▲──────────────────────────▲────────────────────────┘
                                                                │                          │
                                                Painel React (Render static)       API Python no Render: /assistant + /mcp
                                                ingestão · catálogo · KPIs ·      tools + prompts do banco →
                                                risco · assistente · prompts      Claude Desktop / Claude Code
```

Princípio: **a lógica de negócio vive no Postgres** (views e funções em `gold`/`api`). Painel, API do assistente e MCP só consomem — a mesma pergunta dá o mesmo número em qualquer interface.

## 2. Stack

| Camada | Tecnologia | Motivo |
|---|---|---|
| Banco / lake | Supabase Postgres 17 + Storage | Pedido do projeto; SQL, RLS, Realtime e Auth num só lugar |
| Migrations | Supabase CLI (`supabase/migrations/*.sql`) | Reprodutível: `supabase db push` recria tudo |
| Pipeline | Python 3.12+, `psycopg[binary]` 3, `pandas`, `pydantic-settings`, `typer`, `supabase-py` (Storage) | COPY rápido, CLI simples, config tipada |
| Qualidade | `ruff`, `mypy`, `pytest` | Padrão da skill de engenharia |
| Modelo | `scikit-learn` (logística + gradient boosting), `shap` opcional | Interpretável, rápido |
| Painel | Vite + React 18 + TypeScript, Tailwind + shadcn/ui, TanStack Query, Recharts, supabase-js | Rápido de construir, Realtime nativo |
| API do assistente | Python FastAPI (`apps/api`) → Claude API `claude-sonnet-5-5` com tool use | Backend todo em Python; chave da IA fica no servidor (Render) |
| MCP | Python `mcp` (FastMCP), montado na mesma API em `/mcp` (streamable HTTP) + modo stdio local | Um serviço só no Render; conecta no Claude Desktop/Code |
| Repositório | Monorepo em `submissions/tiago-canatelli/` (`apps/`, `packages/`, `supabase/`) | Uma PR, um histórico, deploy por pasta |
| Deploy | Render (Blueprint `render.yaml`) | Static site + web service + cron, cada um com seu `rootDir` |

## 3. Modelo de dados por camada

### 3.1 Landing (data lake raw)
- Bucket `raw`, caminho `raw/<dataset>/<YYYY-MM-DD>/<sha256>.csv` — arquivo imutável, versionado pelo hash.
- Reprocessar = reler do bucket, nunca do disco local.

### 3.2 `bronze` — cópia fiel
- Uma tabela por CSV (`bronze.accounts`, `bronze.subscriptions`, `bronze.feature_usage`, `bronze.support_tickets`, `bronze.churn_events`), **todas as colunas `text`**.
- Colunas técnicas: `_run_id uuid`, `_source_file text`, `_row_number int`, `_row_hash text`, `_ingested_at timestamptz`.
- Idempotência: `unique (_row_hash)`; reingestão do mesmo arquivo não duplica.

### 3.3 `silver` — limpo e tipado
- Tipos corretos (datas, numeric, boolean), `trim`/normalização de categorias, deduplicação pela chave de negócio (última versão por `_ingested_at`).
- PKs e FKs: `accounts(account_id)`, `subscriptions(subscription_id → account_id)`, `feature_usage(subscription_id)`, `support_tickets(account_id)`, `churn_events(account_id)`.
- Linhas rejeitadas vão para `silver._rejects (table, row_hash, reason, payload jsonb)` — nunca somem.
- Transformação via função `silver.refresh(run_id)` (SQL), chamada pelo pipeline.

### 3.4 `gold` — KPIs e marts (fórmulas oficiais na skill `churn-business-analyst`)

| Objeto | Tipo | Grão | Conteúdo |
|---|---|---|---|
| `gold.dim_account` | view | conta | atributos + segmento (plano, indústria, país, canal, trial, faixa de MRR, tempo de casa) |
| `gold.fct_mrr_monthly` | mat. view | conta × mês | MRR início/fim, new, expansion, contraction, churned |
| `gold.kpi_revenue_monthly` | view | mês | MRR, ARR, logo churn %, gross MRR churn %, GRR, NRR, ARPA |
| `gold.kpi_churn_by_segment` | view | segmento | contas, churns, logo churn %, MRR perdido, % do MRR perdido total |
| `gold.kpi_usage_segment_monthly` | mat. view | segmento × mês | uso total, **uso por conta ativa**, contas ativas, erro %, uso beta % |
| `gold.kpi_feature_health` | view | feature | adoção, duração, taxa de erro, churn dos usuários vs não usuários |
| `gold.kpi_support_health` | view | segmento × status (ativo/churn) | tickets/conta, FRT, resolução, CSAT médio, **taxa de resposta CSAT**, % escalado |
| `gold.churn_reason_vs_behavior` | view | evento de churn | motivo declarado, refund, Δ uso 90→30d, erros, tickets e CSAT antes do churn |
| `gold.account_360` | mat. view | conta | tudo acima por conta + flags de sinal de alerta |
| `gold.risk_scores` | tabela | conta ativa × data | probabilidade, top 3 drivers, MRR em risco, ação sugerida, versão do modelo |

### 3.5 `api` — interface pública só leitura
- Views `security_invoker` sobre `gold`/`ops` e funções RPC:
  - `api.get_account_health(account_id)` · `api.list_at_risk_accounts(segment, min_mrr, limit)` · `api.revenue_at_risk(group_by)` · `api.churn_drivers(segment)` · `api.run_readonly_query(sql)` (só `SELECT` em `api.*`, timeout 5s, limite de 500 linhas).
- Único schema exposto no PostgREST. RLS: `authenticated` lê; escrita só em `app.prompt_templates`.

### 3.6 `ops` — operação do lake (alimenta o painel de ingestão)

| Tabela | Campos principais |
|---|---|
| `ops.ingestion_runs` | `run_id`, `started_at`, `finished_at`, `status` (running/success/failed/skipped), `trigger`, `source` (kaggle_mcp/local), `source_version`, `git_sha` |
| `ops.ingestion_steps` | `run_id`, `dataset`, `layer` (raw/bronze/silver/gold), `file_sha256`, `bytes`, `rows_read`, `rows_loaded`, `rows_rejected`, `duration_ms`, `status`, `error` |
| `ops.dq_results` | `run_id`, `check_name`, `table`, `severity`, `status`, `failing_rows`, `sample jsonb` |
| `ops.catalog` | `schema`, `table`, `column`, `data_type`, `description`, `layer`, `business_owner`, `is_pii`, `is_key`, `row_count`, `null_pct`, `distinct_count`, `last_refreshed` |

- `ops.catalog` é gerado de `information_schema` + `COMMENT ON` (descrição escrita em cada migration) + estatísticas calculadas no fim de cada run.
- Realtime habilitado em `ops.ingestion_runs` e `ops.ingestion_steps`: o painel mostra o progresso ao vivo (o pipeline atualiza `rows_loaded` a cada lote).

### 3.7 `app` — assistente de IA

| Tabela | Campos |
|---|---|
| `app.prompt_templates` | `id`, `slug`, `title`, `category` (CEO/CS/Produto/Dados), `description`, `body` (com `{{variaveis}}`), `variables jsonb` (nome, tipo, default), `output_format`, `is_default`, `current_version`, `updated_at`, `updated_by` |
| `app.prompt_versions` | `prompt_id`, `version`, `body`, `variables`, `created_at`, `created_by` — histórico; permite restaurar o padrão |
| `app.ai_runs` | `id`, `prompt_id`, `version`, `rendered_prompt`, `tool_calls jsonb` (queries executadas), `answer`, `model`, `tokens`, `latency_ms`, `created_at` — auditoria e evidência para o process log |

Prompts semente (exemplos): "Por que o churn subiu em {{periodo}}?", "A satisfação está mesmo ok?", "O uso cresceu para todos os segmentos?", "Quais contas o CS deve ligar esta semana?", "Explique o risco da conta {{account_id}}", "Quanto MRR recuperamos se {{acao}}?".

Contrato de resposta (no system prompt, igual para painel e MCP): **Resposta** → **Por quê** (evidências com números e a view de origem) → **Grau de confiança** (correlação vs causa, tamanho de amostra) → **Próxima ação**.

## 4. Pipeline de ingestão

CLI `ravenlake` (Python, `typer`):

```
ravenlake ingest                             # run completo, fonte Kaggle MCP
ravenlake ingest --source ../datasets        # fonte local (offline)
ravenlake ingest --dataset churn_events      # só um dataset
ravenlake dq                                 # só checagens
ravenlake catalog refresh                    # só catálogo
ravenlake score                              # recalcula risk_scores
```

### 4.1 Fonte: Kaggle via MCP

O pipeline busca os dados no **MCP remoto do Kaggle** (`https://www.kaggle.com/mcp`, JSON-RPC sobre HTTP), testado em 2026-10-23: funciona sem login para datasets públicos.

1. `get_dataset_info` → lê `current_version_number` e `last_updated` (hoje: versão 1, de 2025-07-21).
2. Compara com a última versão ingerida em `ops.ingestion_runs.source_version`. Se for igual e os hashes baterem, o run termina como `skipped`.
3. `download_dataset` → devolve uma URL assinada (válida por 3 dias) do `archive.zip`; baixa, descompacta e calcula o sha256 de cada CSV.
4. Segue o fluxo abaixo a partir do upload para `raw/`.

- Adaptadores no `ravenlake`: `KaggleMcpSource` (padrão) e `LocalSource --source datasets/` (fallback offline e testes).
- Token Kaggle opcional (`KAGGLE_MCP_TOKEN`, header bearer) caso o acesso anônimo deixe de funcionar.
- Por que MCP e não a API REST do Kaggle: o endpoint REST de download exige credencial (404 sem login); o MCP entrega a URL assinada sem login e é a mesma interface que o assistente de IA usa.
- Limite honesto: o dataset não muda desde 2025-07, então o cron do Render demonstra o padrão de sincronização incremental, mas na prática vai registrar `skipped`.

### 4.2 Fluxo de `ingest`

1. Abre `ops.ingestion_runs` (status `running`, `source = kaggle_mcp`, `source_version`).
2. Para cada CSV: calcula sha256 → sobe para `raw/` (pula se o hash já existe) → registra step `raw`.
3. `COPY` em lotes para `bronze.*` com `_row_hash`; atualiza `rows_loaded` a cada lote (progresso Realtime) → step `bronze`.
4. `select silver.refresh(run_id)` → step `silver` com rejeitados.
5. Checagens de qualidade → `ops.dq_results`. Severidade `error` interrompe antes do gold.
6. `refresh materialized view` do gold → step `gold`.
7. Atualiza `ops.catalog`; fecha o run com `success`/`failed`.

Checagens de qualidade (mínimo): contagem vs esperado; PK única; órfãos de FK; datas impossíveis (uso após churn, churn antes do signup, fim antes do início); MRR negativo; valores de categoria fora do domínio; % de nulos por coluna; consistência `accounts.churn_flag` × existência de `churn_events`; reativações (churn seguido de nova assinatura).

## 5. Modelo de risco

- Datas de corte mensais; features calculadas só com dados **até** o corte; alvo = churn nos 90 dias seguintes.
- Features: tendência de uso (30 vs 90d), erros/uso, uso de beta, tickets, FRT, escalações, CSAT e **não resposta de CSAT**, downgrade recente, billing, plano, canal, trial, tempo de casa, MRR.
- Validação temporal (treina em cortes antigos, testa nos recentes). Métricas: AUC-PR, lift no top decil, calibração.
- Saída em `gold.risk_scores` com `model_version`; drivers por conta via coeficientes/SHAP.
- Plano B (se o tempo apertar): score por regras com pesos tirados da análise de F3.

## 6. Painel React

Páginas:

| Rota | Para quem | Conteúdo |
|---|---|---|
| `/ingestao` | Dados | Runs (status, duração), progresso ao vivo por dataset/camada, linhas lidas/carregadas/rejeitadas, volume em bytes, histórico |
| `/qualidade` | Dados | Checagens por run, falhas com amostra de linhas |
| `/catalogo` | Todos | Busca por tabela/coluna; camada, descrição, tipo, chave, PII, nulos %, distintos, linhagem raw→bronze→silver→gold |
| `/kpis` | CEO | MRR, ARR, logo vs revenue churn, GRR/NRR, MRR perdido por motivo; os 3 gráficos do paradoxo (CSAT, uso, receita) |
| `/segmentos` | Produto / CEO | Uso por conta por segmento e mês, saúde por feature |
| `/risco` | CS | Fila de contas ordenada por MRR em risco, drivers, ação sugerida, export CSV |
| `/contas/:id` | CS | Visão 360: linha do tempo de assinatura, uso, tickets, score |
| `/assistente` | Todos | Escolhe um prompt pronto, preenche variáveis, edita o texto antes de enviar, vê resposta com "Por quê" e as queries usadas |
| `/prompts` | Todos | Biblioteca de prompts: criar, editar, versionar, restaurar padrão |

Estrutura: `src/pages`, `src/components`, `src/lib/supabase.ts`, `src/hooks/use*.ts` (TanStack Query por view), tipos gerados com `supabase gen types typescript`.

## 7. Assistente de IA

### 7.1 No painel (`apps/api`, endpoint `POST /assistant`)
1. Painel envia `prompt_id`, variáveis e o texto (possivelmente editado), com o JWT do Supabase Auth (a API valida).
2. API renderiza o prompt, chama Claude API (`claude-sonnet-5-5`) com tools: `get_kpi`, `get_account_health`, `list_at_risk_accounts`, `churn_drivers`, `run_readonly_query`.
3. Executa as tools via RPC `api.*` com role read-only; devolve o resultado ao modelo até a resposta final.
4. Grava `app.ai_runs` e retorna resposta + queries usadas.

### 7.2 MCP server (`apps/api`, Python FastMCP montado em `/mcp`)
- **Tools:** as mesmas 5 do painel, chamando as funções `api.*` (conexão com role `analyst_ro`). Tools e endpoint `/assistant` compartilham o mesmo módulo Python.
- **Transporte:** streamable HTTP no Render (protegido por bearer token `MCP_TOKEN`) e stdio para uso local.
- **Prompts MCP:** lidos de `app.prompt_templates` em tempo real — o prompt editado no painel aparece no Claude Desktop/Code sem redeploy.
- **Resources:** `catalog://{schema}/{table}` com descrição e colunas, para a IA saber o que pode consultar.
- Instalação: remoto `claude mcp add --transport http ravenstack-churn https://<api>.onrender.com/mcp --header "Authorization: Bearer <token>"`; local `claude mcp add ravenstack-churn -- uv run ravenstack-mcp` (documentado no README).

## 8. Segurança

| Item | Regra |
|---|---|
| `service_role` key | Só no pipeline local (`.env`), nunca no painel nem no git |
| Painel | `anon` key + login Supabase Auth; lê só `api.*` |
| Role `analyst_ro` | `SELECT` em `api.*`, `statement_timeout` 5s, sem acesso a bronze/silver |
| `run_readonly_query` | Rejeita qualquer coisa que não seja um único `SELECT`; roda em transação read-only |
| Chave Anthropic | Env var secreta do serviço `apps/api` no Render (`sync: false` no Blueprint); MCP usa o cliente do próprio usuário (Claude Desktop/Code) |
| MCP remoto | Bearer token `MCP_TOKEN` (gerado pelo Render com `generateValue`) |
| Advisors | Rodar `get_advisors` (security + performance) ao fim de F2 e F5 |

## 9. Estrutura do monorepo

A raiz do monorepo é `submissions/tiago-canatelli/` (a PR só pode alterar essa pasta).

```
submissions/tiago-canatelli/
├── README.md                         ← template de submissão + setup
├── render.yaml                       ← Blueprint do Render (todos os serviços)
├── .claude/skills/                   ← skills do projeto
├── apps/
│   ├── dashboard/                    ← React (Vite) → Render static site
│   └── api/                          ← FastAPI: /assistant + /mcp + /health → Render web service
├── packages/
│   ├── ravenlake/                    ← pipeline de ingestão (CLI) → Render cron job
│   └── churn_core/                   ← cliente do banco, tools de análise e prompts (usado por api e ravenlake)
├── supabase/
│   ├── migrations/                   ← bronze, ops, silver, gold, api, app, roles
│   └── seed/prompts.sql
├── analysis/                         ← SQL/notebooks das hipóteses
├── model/                            ← treino e avaliação do score de risco
├── report/                           ← relatório do CEO (md + pdf)
├── process-log/                      ← journal, hipóteses, erros da IA, decisões, screenshots, chat exports
└── docs/                             ← planos, arquitetura, dicionário, qualidade
```

- Python: workspace `uv` na raiz (`pyproject.toml` com `[tool.uv.workspace] members = ["apps/api", "packages/*"]`), um `uv.lock` só.
- Node: só `apps/dashboard` (npm).
- O `.gitignore` do repositório ignora `submissions/` e `datasets/` → commitar com `git add -f submissions/tiago-canatelli`; CSVs ficam fora do git.

## 10. Deploy no Render

Blueprint em `submissions/tiago-canatelli/render.yaml`, conectado ao fork no GitHub, branch `submission/tiago-canatelli`. Como o arquivo não fica na raiz do repositório, o caminho do Blueprint é informado ao criar o Blueprint no Render; cada serviço usa `rootDir` e `buildFilter` para só redeployar quando a própria pasta muda.

| Serviço | Tipo Render | `rootDir` | Build / start | Env vars |
|---|---|---|---|---|
| `ravenstack-dashboard` | static site | `apps/dashboard` | `npm ci && npm run build` → publica `dist`; rewrite `/* → /index.html` | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_URL` |
| `ravenstack-api` | web service (Python) | raiz do monorepo | `uv sync --package api` → `uv run uvicorn api.main:app --host 0.0.0.0 --port $PORT`; health check `/health` | `ANALYST_RO_DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_JWT_SECRET`, `ANTHROPIC_API_KEY` (sync: false), `MCP_TOKEN` (generateValue), `PYTHON_VERSION` |
| `ravenstack-ingest` | cron job (opcional) | raiz do monorepo | `uv run ravenlake ingest` (diário; checa versão no Kaggle MCP) | `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |

- O banco continua no Supabase (`G4-Analysys`); o Render não hospeda Postgres.
- Conexão do Render ao Supabase via **pooler** (porta 6543, modo transaction) para não esgotar conexões.
- CORS da API liberado só para a URL do dashboard.
- Ordem de deploy: migrations aplicadas → API (`/health` verde) → dashboard → cron.
- Plano free do Render dorme após inatividade: a primeira chamada pode demorar ~1 min (registrar em Limitações).

## 11. Ordem de implementação

1. Migrations `bronze`, `ops`, `silver` + pipeline até silver + DQ → **M1**
2. Análise das hipóteses direto no silver (SQL/notebook) → **M2**
3. Views gold + `api` + catálogo
4. Painel: `/ingestao`, `/catalogo` → `/kpis`, `/risco` → `/assistente`, `/prompts`
5. `apps/api` (assistente + MCP, compartilham as funções `api.*`) → **M3**
5b. Deploy no Render (API → dashboard → cron)
6. Modelo de risco → `gold.risk_scores`
7. Relatório, README, PR → **M4**

## 12. Testes

| O quê | Como |
|---|---|
| Pipeline | `pytest` com CSVs pequenos de fixture; teste de idempotência (rodar 2x = mesmas contagens) |
| KPIs | Para cada KPI do gold, um teste que recalcula em pandas a partir do CSV e compara |
| `api.run_readonly_query` | Testes negativos: `insert`, `;`, `drop`, acesso a `silver` → todos rejeitados |
| Painel | Smoke test manual no navegador + `tsc --noEmit` + lint |
| MCP | Chamar cada tool via MCP Inspector e registrar print no process log |
