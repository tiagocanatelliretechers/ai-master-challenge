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

### Skill de React/UX, multi-LLM, MCP aberto e RAG
- **Pedido:** melhor experiência no painel, conexão com Claude pelo front, MCP para Claude e outras IAs, chaves de outros LLMs e RAG nas análises.
- **Escolhas:** skill `react-ux-engineer` (shadcn/ui); camada `churn_core.llm` com adaptadores (Anthropic padrão + OpenAI, Gemini, OpenAI-compatível); MCP streamable HTTP documentado por cliente; RAG com pgvector + full-text (busca híbrida) no próprio Supabase.
- **Regra de ouro do RAG:** números sempre das tools (ao vivo); RAG traz contexto e explicação — evita a IA citar número velho de um documento.
- **Custo:** aumenta o escopo; entrou no topo da ordem de cortes.

### Churn = `churn_events` (fonte de verdade)
- **Opções:** `accounts.churn_flag` · `churn_events` · `end_date`/flag da assinatura.
- **Escolha (confirmada pelo Tiago):** `churn_events`; churn é evento recorrente, com reativação.
- **Motivo:** as três fontes discordam (277 contas com evento e flag `False`; 35 com flag `True` sem evento; só 6 de 600 churns coincidem com fim de assinatura). Os eventos têm data, motivo e refund — é a única fonte que permite análise temporal.
- **Consequência:** KPIs de receita dependem de uma regra de MRR vigente ainda a validar; flags viram achado de qualidade no relatório.

### Perfis de análise por área, análise 360 e três camadas de painel
- **Pedido:** skills e RAGs por perfil para análise 360, cobrindo todas as áreas, com perfis padrão personalizáveis; painéis por persona de cliente, por persona analista e um geral.
- **Escolhas:** 8 perfis de fábrica (Executivo, Financeiro, CS, Suporte, Produto, Marketing, Vendas, Dados) em arquivos .md no formato SKILL.md, carregados em `app.analysis_profiles` e editáveis/versionáveis no painel; RAG por perfil via `profile_slugs`; endpoint 360 que roda as lentes em paralelo e sintetiza concordâncias e **discordâncias**; 7 personas de cliente por regra explícita, validadas contra clusterização.
- **Também aceito:** KPIs de concentração de perda e intervalo até reativação; taxa de salvamento em 3 cenários (10/20/30%).
- **Separação importante:** persona analista (quem pergunta) ≠ persona de cliente (sobre quem).
