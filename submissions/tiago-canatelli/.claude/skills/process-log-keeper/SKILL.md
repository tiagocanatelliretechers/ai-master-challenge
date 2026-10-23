---
name: process-log-keeper
description: Mantém o process log obrigatório da submissão do Challenge 001. Use ao terminar uma fase ou hipótese, quando a IA errar e o erro for corrigido, quando uma decisão ou corte de escopo for tomado, ou ao montar o README final de submissão a partir do template.
---

# Process log — evidência de como a IA foi usada

Sem process log a submissão é desclassificada. Ele precisa mostrar **iteração e julgamento**, não "1 prompt → 1 resposta". Registre na hora; reconstruir no final perde os detalhes que mais valem.

## Arquivos

| Arquivo | Quando atualizar | Formato de entrada |
|---|---|---|
| `process-log/journal.md` | fim de cada fase ou bloco de trabalho | `## <data hora> · <fase>` → o que pedi à IA · o que ela fez · o que ajustei · próximo passo |
| `process-log/ai-errors.md` | sempre que a IA errar | `### <título>` → o que a IA fez · como percebi · como corrigi · lição |
| `process-log/decisions.md` | decisão, trade-off ou corte de escopo | `### <decisão>` → opções · escolha · motivo · impacto |
| `process-log/hypotheses.md` | cada hipótese (formato na skill `churn-data-scientist`) | — |
| `process-log/screenshots/` | painel, MCP Inspector, Claude respondendo, Supabase | `<fase>-<descricao>.png` |
| `process-log/chat-exports/` | fim de cada sessão de IA | export do transcript |

## Tipos de erro da IA que valem registro

Número inventado ou não conferido · coluna/tabela assumida que não existe · conclusão causal sem teste · leakage no modelo · KPI com fórmula diferente do dicionário · código que roda mas faz a coisa errada · recomendação genérica · excesso de escopo.

## Ao fechar uma fase

1. Atualizar `journal.md`.
2. Conferir se houve erro da IA ou decisão não registrada.
3. Tirar screenshot do que foi construído.
4. Commit com mensagem que explique o porquê.

## Montar o README final

Use `../../templates/submission-template.md` (raiz do repositório) **sem mudar a estrutura**. Mapeamento:

| Seção | Fonte |
|---|---|
| Sobre mim | Nome, LinkedIn, "Challenge 001 — Diagnóstico de Churn" |
| Executive Summary | 3–5 frases do relatório do CEO |
| Abordagem | `docs/01-plano-projeto.md` + `decisions.md` |
| Resultados / Findings | hipóteses confirmadas com números + links para painel/relatório |
| Recomendações | lista priorizada (formato da skill `churn-business-analyst`) |
| Limitações | dataset sintético, hipóteses inconclusivas, causas não validadas por experimento, cortes de escopo |
| Ferramentas usadas | tabela ferramenta → uso real |
| Workflow | resumo numerado do `journal.md` |
| Onde a IA errou | melhores casos de `ai-errors.md` |
| O que eu adicionei | julgamento: hipóteses escolhidas, testes de causalidade cobrados, priorização por MRR, cortes |
| Evidências | marcar o que existe e linkar arquivos/pastas |
