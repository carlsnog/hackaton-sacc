# Limitações conhecidas

## Dados ausentes

- Não há crosswalk oficial TSE-IBGE local. A ponte atual usa nomes normalizados para construir uma correspondência auditável dos 223 municípios.
- Não há dados eleitorais por seção. Deduplicação e auditoria por zona/seção não são executáveis com o CSV atual.
- O arquivo eleitoral local possui totais agregados municipais, mas não documentação suficiente para interpretar `QT_APTOS` como eleitores únicos estaduais. A taxa é preservada; o cartão usa o total estadual informado separadamente.

## Decisões deliberadas

- A renda é atualizada somente pela API oficial SIDRA configurada; nenhuma lacuna é preenchida por estimativa.
- O SQLite substitui PostgreSQL no MVP executável local. O repository isola a futura troca.
- O assistente não chama LLM externo por padrão. O comportamento quantitativo já funciona via tools locais.

## Próxima ampliação de dados

Quando novos arquivos locais forem adicionados, priorizar: crosswalk oficial e eleitoral por seção com metadados completos de eleição e turno. O pipeline deve evoluir preservando os schemas canônicos.
