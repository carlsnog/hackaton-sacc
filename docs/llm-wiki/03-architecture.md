# Arquitetura

## Princípios

- Separação entre ingestão, transformação, persistência, consulta, apresentação e IA.
- Adapter/repository para isolar SQLite e permitir migração futura a PostgreSQL.
- Configuração externa para caminhos, score, guardrails, prompts e nomes de variáveis de credencial.
- Snapshot derivado de hashes das fontes e configuração do score.
- Degradação explícita quando um requisito depende de dado local ausente.

## Componentes

| Caminho | Responsabilidade |
| --- | --- |
| `pipeline/core.py` | normalização, hashes, percentis e correlações |
| `pipeline/run_pipeline.py` | carga local, qualidade, crosswalk, mart e documentos RAG |
| `pipeline/schema.sql` | modelo SQLite auditável |
| `app/repositories/analytics.py` | consultas parametrizadas e whitelist de ordenação |
| `app/main.py` | API HTTP e arquivos estáticos |
| `ai/assistant.py` | roteamento determinístico para tools e política de recusa |
| `frontend/` | cards, scatter, ranking, exportação e chat |
| `config/` | comportamento editável sem alteração de código |

## Fluxo

`API SIDRA oficial -> CSV local -> validação -> fatos -> dimensão territorial local -> mart completo -> SQLite -> API -> dashboard/assistant`.

Artefatos reconstruíveis ficam em `data/curated`, `data/reports` e `data/rag`, ignorados pelo Git.
