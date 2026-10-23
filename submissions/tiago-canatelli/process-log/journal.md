# Journal — Challenge 001

## 2026-10-23 · F0/F1 Setup e planejamento
- **Pedi à IA (Claude Code):** clonar o repositório, ler o challenge, guia e template, e planejar a execução com Supabase (data lake), painéis, MCP e skills.
- **A IA fez:** clonou o repo, leu os docs, verificou ferramentas locais (Python 3.14, Supabase CLI, gh), descobriu que o download do Kaggle exige autenticação e que o `.gitignore` ignora `submissions/`. Gerou um primeiro plano único.
- **Ajustei:** pedi a separação em plano de projeto (negócio) e plano técnico, e skills por papel (cientista de dados, business, engenharia Python), além de painel React de ingestão/catálogo e assistente com prompts editáveis.
- **Resultado:** `docs/01-plano-projeto.md`, `docs/02-plano-tecnico.md`, 4 skills em `.claude/skills/`.
- **Bloqueio:** criação do projeto Supabase `ravenstack-churn` falhou — limite de 2 projetos free ativos na organização.
- **Próximo:** liberar o Supabase, baixar dados, F2 (ingestão).

## 2026-10-23 · Validação da fonte de dados
- **Pedi à IA:** confirmar se o dataset do Kaggle é a base do projeto.
- **A IA fez:** abriu a página do dataset no navegador e leu o README do autor: schema completo, edge cases declarados (reativações, nulos, mudanças de plano, picos de beta), exigência de crédito ao autor e um notebook público sobre rejeição de 25.000 linhas.
- **Ajustei:** a skill do cientista de dados tinha nomes de colunas *supostos*; troquei pelo schema real e transformei os edge cases em checagens obrigatórias.

## 2026-10-23 · Download dos dados via MCP do Kaggle
- **Pedi à IA:** baixar o dataset pelo MCP remoto do Kaggle e avaliar sincronizar o Supabase por ele.
- **A IA fez:** testou o endpoint `https://www.kaggle.com/mcp` direto por JSON-RPC (76 tools; `download_dataset` funciona sem login e devolve URL assinada), baixou o zip para `datasets/kaggle-rivalytics/` e conferiu: 500 / 5.000 / 25.000 / 2.000 / 600 linhas, cabeçalhos iguais ao schema da skill. `get_dataset_info`: versão 1, atualizada em 2025-07-21.
- **Decisão:** o pipeline usa o Kaggle MCP como fonte, com checagem de versão + sha256 (ver `decisions.md`).
- **sha256:** accounts `348d8ba9…`, churn_events `6391c41d…`, feature_usage `c081da2b…`, subscriptions `dcf1d93c…`, support_tickets `ba000695…`.

## 2026-10-23 08:50–09:25 · F1 · Revisão das skills uma a uma
- **Pedi à IA:** revisar cada skill comigo antes de começar a execução.
- **A IA fez:** antes de apresentar cada skill, conferiu as regras nos CSVs: 77% do uso tem data anterior ao início da assinatura; as três definições de churn discordam; churn e assinaturas não se cruzam (só 6 de 600 churns coincidem com o fim de uma assinatura); `feedback_text` tem só 4 textos distintos; o churn por trimestre vai de 6 → 251.
- **Verifiquei / ajustei:**
  - escolhi `churn_events` como fonte de verdade;
  - pedi uma skill de React/UX, multi-LLM, MCP aberto para outras IAs e RAG;
  - pedi perfis de análise por área com RAG próprio e análise 360, além de painéis geral, por área e por persona de cliente;
  - decidi que tudo roda no Supabase SaaS, sem Docker.
- **Resultado:** 5 skills revisadas. Commits `3701de5`, `9ecaebe`, `f4557e8`, `4da3719`, `d0defc4`.
- **Próximo:** F2 — migrations e ingestão no Supabase.

## 2026-10-23 09:40–10:20 · F2 · Migrations e pipeline
- **Pedi à IA:** começar a F2 com migrations e ingestão no Supabase G4-Analysys.
- **A IA fez:**
  - inspecionou os formatos reais dos CSVs;
  - escreveu e aplicou 5 migrations: schemas, `ops`, bronze, silver com `silver.refresh`, qualidade (`ops.run_dq`, 16 checagens) e catálogo (`ops.refresh_catalog`);
  - validou a camada SQL com um teste de fumaça desfeito no final (`raise exception` dentro de um bloco `DO`, que força rollback): rejeição de linhas inválidas, colisão de `usage_id`, CSAT nulo, checagens e catálogo;
  - criou o pacote `ravenlake`: fonte Kaggle via SDK do MCP, upload para o bucket `raw`, COPY em lotes para o bronze e progresso em `ops.ingestion_steps`.
- **Verifiquei / ajustei:**
  - os `usage_id` duplicados (21) **não** são linhas repetidas, são eventos diferentes com o mesmo id; ficam mantidos com sufixo `#n`;
  - o CSAT só tem notas 3, 4 e 5 (nenhuma 1 ou 2), o que virou uma checagem;
  - o SDK do MCP 2.3 mudou a API (`streamable_http_client`, `is_error`), e o código foi ajustado;
  - o `uv` não instalou pelo Homebrew; foi instalado pelo PyPI num ambiente virtual dedicado.
- **Resultado:** `ravenlake version` → 1 (Kaggle MCP ok); lint, mypy e testes passando; advisors só com INFO de RLS sem policy, o que é intencional porque o acesso virá pela camada `api`.
- **Próximo:** credenciais no `.env` → `ravenlake ingest`.

## 2026-10-23 10:30–10:50 · F2 · Primeira ingestão real
- **Pedi à IA:** rodar a ingestão completa depois de eu preencher o `.env`.
- **A IA fez:**
  - conferiu o `.env` sem expor segredos e pegou que a `DATABASE_URL` estava com a URL HTTP do projeto em vez da connection string do Postgres;
  - rodou `ravenlake ingest`: Kaggle MCP → 5 arquivos no bucket `raw` → 33.100 linhas no bronze (feature_usage em 5 lotes) → silver com 0 rejeitadas → 16 checagens → catálogo com 16 tabelas e 205 colunas, em 108 s;
  - conferiu os totais de controle do silver contra os CSVs;
  - rodou de novo para testar idempotência.
- **Verifiquei / ajustei:** os totais de controle batem com o CSV (MRR 11.338.747, uso 250.525, CSAT 4.678, refunds 8.652,25); o segundo run deu `skipped`, sem duplicar o bronze; os sha256 batem com os do download manual.
- **Resultado:** `docs/data-quality.md`. Run `3f3c24da` (success) e `f0133317` (skipped).
- **Próximo:** F3 — diagnóstico (hipóteses) sobre o silver.
