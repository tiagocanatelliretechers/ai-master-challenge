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
