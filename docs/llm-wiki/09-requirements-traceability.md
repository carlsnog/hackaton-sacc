# Rastreabilidade dos requisitos

## Implementado com dados locais

| Área | Entrega |
| --- | --- |
| Pipeline | Leitura local configurável, hashes, manifesto, snapshot, dimensão territorial auditável, fatos e mart |
| Qualidade | Schema obrigatório, universo PB, unicidade TSE, reconciliação eleitoral, limites percentuais, soma de faixas e alertas estruturados |
| Indicadores | Taxa ponderada, percentis, score configurável, Pearson, Spearman, delta municipal e grupos por renda |
| API | Resumo, lista paginada, detalhe, rankings, grupos, exportações CSV, status e healthcheck |
| Dashboard | Cards explicativos, mapa de calor com fallback, scatter plot com escalas, tabela ordenável, grupos de renda e exportações |
| IA | Tools determinísticas, RAG reconstruível, prompts externos, nomes de variáveis de credencial configuráveis e recusa neutra |
| Operação | Containerfile, Compose, `.env.example`, Makefile Podman e testes containerizados |

## Degradação controlada

| Requisito | Motivo | Comportamento atual |
| --- | --- | --- |
| Mapa de calor | `data/geo` não contém GeoJSON ou TopoJSON | Componente pronto; exibe fallback até receber `data/geo/municipios-pb.geojson` |
| Crosswalk oficial | Arquivo TSE-IBGE não está disponível localmente | Fallback por nome normalizado somente para construir ponte auditável |
| Auditoria por seção | Eleitoral local já está agregado por município | Pipeline valida unicidade municipal e documenta indisponibilidade de seção |
| Cobertura de 223 municípios no mart | SIDRA local possui somente 10 municípios | Mart parcial, aviso de cobertura e lista de ausentes |
| LLM externo e índice vetorial | Nenhum provedor ou banco vetorial foi fornecido | Assistente determinístico e documentos RAG JSON reconstruíveis |
| PostgreSQL | Ambiente local inicial usa biblioteca padrão | SQLite isolado por repository para substituição futura |

## Não implementar sem novos arquivos locais

Não preencher as lacunas por download, estimativa ou fonte externa. Quando novos arquivos forem adicionados em `data/`, preservar os schemas canônicos e remover cada degradação com testes específicos.
