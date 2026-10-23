# Onde a IA errou e como corrigi

_(registrar em tempo real — skill `process-log-keeper`)_

### Schema assumido em vez de verificado
- **O que a IA fez:** a primeira versão da skill de dados listou colunas e chaves deduzidas do README do challenge (ex.: "canal de aquisição", "CSAT de pesquisa").
- **Como percebi:** ao conferir o README original do dataset no Kaggle — os nomes reais são `referral_source`, `satisfaction_score` nos tickets, `is_reactivation` etc.
- **Correção:** skill atualizada com o schema real e com a regra "inspecionar antes de usar".
- **Lição:** documentação de segunda mão não é fonte; ir na origem.

### RAG sobre feedback de clientes proposto sem olhar o dado
- **O que a IA fez:** planejou clusterizar `feedback_text` por tema no RAG para testar a H4.
- **Como percebi:** ao validar os KPIs nos CSVs — só existem 4 textos de feedback distintos em 452 preenchidos.
- **Correção:** análise semântica descartada; H4 será testada com comportamento (uso, erros, tickets). RAG focado no conhecimento das análises.
- **Lição:** checar o conteúdo antes de desenhar a solução — de novo.

### Skill de engenharia desatualizada em relação ao próprio plano
- **O que a IA fez:** a cada mudança de escopo (Render, multi-LLM, RAG, perfis) foi anexando seções na skill de engenharia sem reorganizar; ficaram tools com nomes diferentes do plano (`query_analytics` × `run_readonly_query`), dependências faltando (OpenAI, Gemini, cliente do Kaggle MCP), endpoint 360 sem regra de concorrência e auth assumindo o segredo JWT legado do Supabase.
- **Como percebi:** na revisão da skill, lendo de ponta a ponta.
- **Correção:** skill reescrita com rotas, tools únicas, dependências por pacote, pooler em modo transaction (sem prepared statements), JWT via JWKS, limites de custo e testes por camada.

### API do SDK do MCP assumida de memória
- **O que a IA fez:** escreveu o cliente do Kaggle com `streamablehttp_client(url, headers=…)` e `result.isError`, a API de versões antigas do SDK.
- **Como percebi:** `mypy` e o import falharam com o `mcp` 2.3 instalado.
- **Correção:** inspecionei a assinatura real no pacote instalado e usei `streamable_http_client` + `create_mcp_http_client(headers=…)` + `is_error`.
- **Lição:** conferir a API da versão instalada antes de escrever integração.

### Checagem de qualidade com total errado
- **O que a IA fez:** a checagem `linhas_rejeitadas` usava como total só accounts + subscriptions.
- **Como percebi:** revisando a saída do teste de fumaça.
- **Correção:** nova migration; o total passou a ser as linhas lidas pelo silver no run.

### `git add -f` commitou `.venv` e caches (4.306 arquivos)
- **O que a IA fez:** usou `git add -f` na pasta da submissão. O `-f` ignora também o `.gitignore` interno, e entraram `.venv`, `.mypy_cache` e outros caches.
- **Como percebi:** pela lista do `git status` logo após o commit.
- **Correção:** o commit ainda era local; foi refeito com `--amend` sem esses arquivos. Criei `scripts/stage.sh`, que faz `git add -f` e depois remove o que o `.gitignore` da pasta ignora, e a skill de engenharia agora proíbe `git add -f` direto.
