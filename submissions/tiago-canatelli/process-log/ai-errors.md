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
