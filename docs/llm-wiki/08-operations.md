# Operação

## Comandos

```bash
make pipeline
make test
make serve
podman compose up --build
make ingest
make deploy-snapshot
```

Todos os alvos `make` constroem ou executam a imagem `vozes-ausentes-pb:dev` via Podman. Não execute testes diretamente com o Python do host.

## Snapshot

O snapshot é derivado dos hashes dos dois arquivos consumidos, de `pipeline_version` e da configuração de score. Reexecutar o pipeline registra nova execução, mas mantém as linhas imutáveis do mesmo snapshot por inserção idempotente.

## Testes

`make test` executa `python -m unittest discover -s tests -v` dentro do Podman. A suíte valida ingestão SIDRA, normalização nominal, marcadores nulos, denominador zero, percentis, correlações, universo eleitoral, mart completo, reconciliação, soma dos pesos, qualidade de faixas, RAG, repositório e assistente.

## Evolução

1. Adicionar fontes novas somente como arquivos locais versionados ou montados no ambiente.
2. Implementar adaptadores de ingestão separados sem alterar consultas analíticas.
3. Substituir `AnalyticsRepository` por uma implementação PostgreSQL mantendo contratos.
4. Ativar um adapter LLM separado, lendo credenciais exclusivamente do ambiente.
5. Manter a malha municipal de `data/geo` associada por código IBGE.

## Deploy Vercel sem LLM

O frontend, o mapa, a API e o assistente baseado em regras podem ser publicados na Vercel sem credenciais externas. `api/index.py` reutiliza o handler HTTP da aplicação e `vercel.json` encaminha todas as rotas para a Function Python.

Antes do deploy, execute `make pipeline`, `make test` e `make deploy-snapshot`. O último comando gera `data/deploy/vozes_ausentes_pb.sqlite3`, cópia somente leitura que deve ser versionada. A Vercel não executa Podman nem refaz a ingestão SIDRA durante o build.
