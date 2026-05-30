# Pipeline e qualidade

Execute `make pipeline`. A mesma combinação de entradas, versão do pipeline e pesos gera o mesmo `snapshot_id`, sem duplicar nem sobrescrever fatos publicados. Mudanças de transformação devem incrementar `pipeline_version` em `config/settings.json`.

## Tabelas

| Tabela | Grão efetivo |
| --- | --- |
| `pipeline_run` | execução |
| `source_manifest` | snapshot x fonte |
| `dim_municipio` | snapshot x código TSE |
| `fact_abstencao_municipio` | snapshot x eleição x turno x município TSE |
| `fact_renda_municipio` | snapshot x município IBGE x período |
| `mart_municipio_eleicao` | snapshot x município IBGE x eleição x turno x renda |

## Qualidade validada

- Eleitoral PB contém exatamente 223 municípios.
- Código TSE é único no agregado municipal local.
- `aptos = comparecimento + abstenções` para todas as linhas.
- Taxas e percentuais permanecem no intervalo `0` a `100`.
- Percentuais municipais por faixa somam entre `99,9%` e `100,1%`.
- Mart publica os 223 municípios, exatamente a cobertura socioeconômica local.
- Relatório detalhado: `data/reports/<snapshot_id>.json`.
- Documentos contextuais reconstruíveis: `data/rag/<snapshot_id>/<cod_ibge>.json`.

O relatório possui mensagens estruturadas com `level`, `code` e detalhes. O snapshot atual registra `CROSSWALK_IBGE_CODE`: o arquivo combinado contém código IBGE e permite associar os 223 municípios sem fallback nominal.

## Score

`100 * (0,40 * percentil_abstencao + 0,35 * percentil_renda_baixa + 0,25 * percentil_baixa_renda)`.

Pesos e versão ficam em `config/settings.json`. O pipeline falha se os pesos não somarem `1`.
