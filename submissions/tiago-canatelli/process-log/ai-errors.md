# Onde a IA errou e como corrigi

_(registrar em tempo real — skill `process-log-keeper`)_

### Schema assumido em vez de verificado
- **O que a IA fez:** a primeira versão da skill de dados listou colunas e chaves deduzidas do README do challenge (ex.: "canal de aquisição", "CSAT de pesquisa").
- **Como percebi:** ao conferir o README original do dataset no Kaggle — os nomes reais são `referral_source`, `satisfaction_score` nos tickets, `is_reactivation` etc.
- **Correção:** skill atualizada com o schema real e com a regra "inspecionar antes de usar".
- **Lição:** documentação de segunda mão não é fonte; ir na origem.
