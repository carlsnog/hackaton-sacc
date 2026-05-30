# Guia de continuação

## Ordem curta de leitura

1. Leia `00-index.md`, `02-local-data-catalog.md`, `07-known-limitations.md` e `09-requirements-traceability.md`.
2. Leia `config/settings.json` antes de alterar regras analíticas.
3. Leia `config/ai.json` e `ai/prompts/` antes de alterar comportamento assistido.
4. Execute `make test`; a validação deve ocorrer somente dentro do Podman.

## Invariantes

- Use arquivos locais em `data/`; atualize renda somente pelo ingestor SIDRA oficial configurado.
- Não trate código TSE como código IBGE.
- Não use nome municipal como chave analítica final.
- Preserve o alinhamento temporal atual: renda média, mediana e faixas usam 2022.
- Não apresente correlação como causalidade.
- Não delegue aritmética, ranking ou filtros ao modelo de linguagem.
- Não silencie fallback territorial ou limitações do arquivo eleitoral agregado.

## Pontos de extensão

| Necessidade | Ponto inicial |
| --- | --- |
| Atualizar renda SIDRA | `config/sidra.json` e `pipeline/ingest_sidra.py` |
| Crosswalk oficial local | substituir fallback em `pipeline/run_pipeline.py::build_crosswalk` |
| Dados eleitorais por seção | criar fato de seção e agregador antes de `load_electoral` |
| PostgreSQL | nova implementação da interface prática de `AnalyticsRepository` |
| Provedor LLM | adapter separado lendo somente nomes de ambiente de `config/ai.json` |
| Mapa | manter `data/geo/geojs-25-mun.json`; o frontend associa `properties.id` ao código IBGE |

## Artefatos reconstruíveis

`data/curated/`, `data/reports/` e `data/rag/` não devem receber edição manual. Use `make pipeline`.
