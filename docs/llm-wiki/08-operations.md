# Operação

## Comandos

```bash
make pipeline
make test
make serve
podman compose up --build
```

Todos os alvos `make` constroem ou executam a imagem `vozes-ausentes-pb:dev` via Podman. Não execute testes diretamente com o Python do host.

## Snapshot

O snapshot é derivado dos hashes dos dois arquivos consumidos, de `pipeline_version` e da configuração de score. Reexecutar o pipeline registra nova execução, mas mantém as linhas imutáveis do mesmo snapshot por inserção idempotente.

## Testes

`make test` executa `python -m unittest discover -s tests -v` dentro do Podman. A suíte valida normalização nominal, marcadores nulos, denominador zero, percentis, correlações, universo eleitoral, mart parcial, reconciliação, soma dos pesos, qualidade de faixas, RAG, repositório e assistente.

## Evolução

1. Adicionar fontes novas somente como arquivos locais versionados ou montados no ambiente.
2. Implementar adaptadores de ingestão separados sem alterar consultas analíticas.
3. Substituir `AnalyticsRepository` por uma implementação PostgreSQL mantendo contratos.
4. Ativar um adapter LLM separado, lendo credenciais exclusivamente do ambiente.
5. Adicionar `data/geo` e um componente cartográfico quando houver geometria local.
