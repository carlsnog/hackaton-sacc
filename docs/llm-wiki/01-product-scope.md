# Produto e escopo

## Objetivo

Analisar associação territorial entre renda domiciliar per capita e abstenção eleitoral municipal na Paraíba. A aplicação fornece pipeline, snapshot auditável, API, dashboard e assistente local.

## Regras de domínio

- A granularidade publicada é município x eleição x turno x período de renda.
- Toda métrica quantitativa vem de SQL ou função determinística.
- O modelo de linguagem, quando habilitado futuramente, interpreta resultados de tools; não calcula rankings.
- Correlação descreve associação e não demonstra causalidade.
- O score é exploratório, versionado e reproduzível.
- Não há dados pessoais, inferência de voto, persuasão segmentada ou recomendação partidária.

## Recorte efetivo

- Eleitoral: PB, 2022, turno local sintético `1`, 223 municípios.
- Renda média e mediana: 2022, 223 municípios.
- Faixas de renda por moradores: 2022, 223 municípios.
- Snapshot validado: `bb335b97e6c9d9e2` (`pipeline_version=local-mvp-v3`).
