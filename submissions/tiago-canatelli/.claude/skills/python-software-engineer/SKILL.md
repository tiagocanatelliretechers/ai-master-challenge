---
name: python-software-engineer
description: Engenheiro de software sênior e especialista em Python do monorepo RavenStack Churn Lake. Use ao escrever ou revisar código do pipeline de ingestão (ravenlake), migrations Supabase, funções SQL da camada api, a API FastAPI com assistente e MCP, o painel React, deploy no Render (render.yaml), testes, configuração, segurança de segredos e instruções de setup.
---

# Engenharia de software — RavenStack Churn Lake

Arquitetura e contratos: `docs/02-plano-tecnico.md`. Monorepo com raiz em `submissions/tiago-canatelli/` (`apps/`, `packages/`, `supabase/`). Avaliadores vão ler o código e rodar o setup: **simples, legível, reproduzível**.

## 1. Princípios

- Lógica de negócio no Postgres (`gold`/`api`); Python e React só orquestram e exibem.
- Idempotência: rodar duas vezes = mesmo estado.
- Nada some em silêncio: erros vão para `ops.ingestion_steps.error`, linhas ruins para `silver._rejects`.
- Menor código que resolve. Sem abstrações para casos que não existem.
- Segredos só em `.env` (no `.gitignore`) e `.env.example` versionado com chaves vazias.

## 2. Python

- Python ≥ 3.12, workspace `uv` na raiz do monorepo (membros `apps/api`, `packages/ravenlake`, `packages/churn_core`), um `uv.lock`. Código compartilhado (cliente do banco, tools, prompts) só em `churn_core`.
- Layout `src/<pacote>/`, testes em `tests/`.
- Dependências: `psycopg[binary]>=3`, `pandas`, `pydantic-settings`, `typer`, `supabase` (Storage), `rich` (log), `fastapi` + `uvicorn` (API), `mcp` (MCP), `anthropic` (assistente), `scikit-learn` (modelo). Não adicionar outras sem motivo registrado.
- Tipagem completa; `ruff check` + `ruff format` + `mypy --strict` limpos antes de commit.
- Config: classe `Settings(BaseSettings)` lendo `.env` (`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `DATABASE_URL`, `ANALYST_RO_DATABASE_URL`).
- Banco: `psycopg` com `COPY ... FROM STDIN` em lotes (5k linhas) para bronze; parâmetros sempre bindados, nunca f-string em SQL com valores.
- Logging estruturado com `run_id` em toda linha; progresso gravado em `ops.ingestion_steps` a cada lote (alimenta o Realtime do painel).
- Erros: capturar na borda do step, gravar em `ops`, marcar `failed`, relançar. Nunca `except: pass`.
- CLI com `typer`: `ravenlake ingest | dq | catalog refresh | score`.

## 3. SQL e migrations

- Uma migration por mudança lógica: `supabase/migrations/<timestamp>_<descricao>.sql`. Nunca editar migration já aplicada; criar nova.
- Schemas: `bronze`, `silver`, `gold`, `api`, `ops`, `app`. Só `api` exposto no PostgREST.
- `COMMENT ON` em toda tabela e coluna (alimenta o catálogo).
- Views de `api` com `security_invoker = true`; funções `api.*` `stable`, `security definer` só quando necessário e com `search_path` fixo.
- Role `analyst_ro`: `USAGE` + `SELECT` em `api`, `statement_timeout = '5s'`.
- `api.run_readonly_query(sql)`: aceita um único `SELECT`/`WITH`, roda em transação `read only`, limita a 500 linhas; recusar `;` múltiplo, DDL, DML e schemas fora de `api`.
- Rodar `get_advisors` (security e performance) após cada bloco de migrations e corrigir avisos.

## 4. API e MCP (`apps/api`)

- FastAPI com `/health`, `POST /assistant` (valida JWT do Supabase) e FastMCP montado em `/mcp` (streamable HTTP, bearer `MCP_TOKEN`); entrypoint `ravenstack-mcp` para stdio local. Conexão com `ANALYST_RO_DATABASE_URL` (pooler 6543).
- Tools finas que chamam `api.*`: `get_account_health`, `list_at_risk_accounts`, `revenue_at_risk`, `churn_drivers`, `query_analytics`. Docstrings claras (são o que o modelo lê).
- Prompts MCP carregados de `app.prompt_templates` a cada `list_prompts` (sem cache longo), variáveis viram argumentos do prompt.
- Resource `catalog://{schema}/{table}` a partir de `ops.catalog`.
- Retornos em JSON compacto com os números e a view de origem, para a IA conseguir citar o "por quê".

## 5. Assistente (`POST /assistant`)

- Recebe `{prompt_id, variables, edited_body?}`; renderiza; chama a Claude API (SDK `anthropic`, modelo `claude-sonnet-5-5`) com tool use usando as mesmas tools do MCP.
- `ANTHROPIC_API_KEY` só como env var secreta no Render. Loop de tools com limite (ex.: 6 iterações).
- Grava `app.ai_runs` (prompt renderizado, tool calls, resposta, tokens, latência).
- Consulte a skill `claude-api` antes de escrever a chamada à API.

## 6. Painel React

- Vite + React 18 + TypeScript strict, Tailwind + shadcn/ui, TanStack Query, Recharts, `@supabase/supabase-js`.
- Tipos gerados: `supabase gen types typescript --schema api > src/lib/database.types.ts`.
- Um hook por view (`useIngestionRuns`, `useCatalog`, `useKpiRevenue`, `useRiskQueue`...). Realtime via `supabase.channel()` em `ops.ingestion_runs`/`ops.ingestion_steps`.
- Só a `anon` key no front (`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`).
- Toda tela trata loading, vazio e erro. Números formatados em pt-BR (`Intl.NumberFormat`), moeda em USD.
- Gráficos: siga a skill `dataviz`.
- `npm run build` e `tsc --noEmit` limpos antes de commit.

## 7. Deploy no Render

- Blueprint único em `render.yaml` na raiz do monorepo (seção 10 do plano técnico): static site `apps/dashboard`, web service `ravenstack-api`, cron `ravenstack-ingest`.
- `buildFilter.paths` por serviço para não redeployar tudo a cada commit.
- Segredos com `sync: false` ou `generateValue: true`; nunca valores no YAML.
- Use as skills `render:render-blueprints` e `render:render-deploy` antes de mexer no Blueprint; validar com `render blueprints validate`.
- Depois do deploy: `/health` verde, dashboard abre, MCP responde no Inspector.

## 8. Testes

- Pipeline: fixtures CSV pequenas em `tests/fixtures`; teste de idempotência; teste de rejeição.
- KPIs: recalcular em pandas a partir do CSV e comparar com a view gold (tolerância 0.01).
- Segurança: testes negativos de `run_readonly_query`.
- MCP: rodar cada tool no MCP Inspector e salvar print em `process-log/screenshots/`.

## 9. Git

- Branch `submission/tiago-canatelli`; só alterar `submissions/tiago-canatelli/`.
- O `.gitignore` raiz ignora `submissions/`: usar `git add -f`.
- Commits pequenos, um por passo, mensagem no imperativo explicando o porquê — o histórico é evidência do process log.
- Nunca commitar `.env`, CSVs de dados ou `node_modules`.

## 10. README de setup (sempre atualizado)

Pré-requisitos → `.env` → `supabase db push` → baixar dados → `uv run ravenlake ingest` → `uv run uvicorn api.main:app` → `npm run dev` → registrar o MCP no Claude → links do deploy no Render. Testar o passo a passo do zero antes do PR.
