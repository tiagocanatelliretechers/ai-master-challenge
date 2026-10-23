# Decisões

### Lógica de negócio no Postgres (gold/api)
- **Opções:** calcular KPIs no Python, no React ou no banco.
- **Escolha:** views e funções no banco.
- **Motivo:** painel, Edge Function e MCP mostram o mesmo número para a mesma pergunta.

### Prompts do assistente no banco (`app.prompt_templates`)
- **Opções:** prompts fixos no código / arquivo / tabela.
- **Escolha:** tabela com versões.
- **Motivo:** editáveis pelo painel e expostos como prompts MCP sem redeploy.

### Corte de escopo pré-definido
- **Motivo:** o escopo (~8h) passa do budget de 4–6h do desafio.
- **Regra:** cortar modelo → MCP → catálogo, nessa ordem. Diagnóstico e relatório não encolhem.

### Monorepo + deploy no Render
- **Pedido:** trabalhar como monorepo e fazer os deploys no Render.
- **Escolha:** raiz do monorepo em `submissions/tiago-canatelli/` (regra da PR); `apps/dashboard` (static site), `apps/api` (FastAPI com `/assistant` + `/mcp`), `packages/ravenlake` (cron), `packages/churn_core` (compartilhado); Blueprint `render.yaml`.
- **Consequência:** a Edge Function do Supabase prevista antes foi substituída pela API Python no Render — backend todo em uma linguagem, e assistente e MCP num serviço só.

### Fonte de dados: Kaggle MCP no pipeline
- **Opções:** download manual · API REST do Kaggle com token · MCP remoto do Kaggle.
- **Escolha:** MCP do Kaggle (`get_dataset_info` + `download_dataset`), com fonte local como fallback.
- **Motivo:** funciona sem credencial; permite sincronização incremental por versão; REST exige token.
- **Ressalva:** o dataset está na versão 1 desde 2025-07-21 — a sincronização é demonstrativa.
