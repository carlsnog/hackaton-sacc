# Catálogo dos dados locais

## Eleitoral

Arquivo: `data/dados_socioeconomicos_e_eleitorais.csv`.

O arquivo combinado preserva os agregados eleitorais locais e acrescenta código IBGE, `pib_mil_reais`, totais por sexo e categorias de escolaridade. A origem deve ser comunicada separadamente: TSE para eleição de 2022 e IBGE para indicadores municipais. O arquivo local não explicita o ano de referência do PIB.

Grão real: uma linha por município, já agregado. Não existem eleição, turno, zona ou seção no arquivo. O pipeline atribui `ano_eleicao=2022`, `turno=1` e `cod_eleicao=LOCAL-2022`, deixando explícita a adaptação.

| Campo | Tipo inferido | Uso |
| --- | --- | --- |
| `SG_UF` | string(2) | filtro PB |
| `CD_MUNICIPIO` | string | código TSE |
| `NM_MUNICIPIO` | string | exibição e auditoria |
| `QT_APTOS` | int | denominador |
| `QT_COMPARECIMENTO` | int | reconciliação |
| `QT_ABSTENCAO` | int | numerador |
| `VOTOS_BRANCOS`, `VOTOS_NULOS` | int | indicadores complementares |
| `PCT_*` | decimal | valores originais; a taxa de abstenção é recalculada |

Resumo validado: 223 linhas; 6.183.368 aptos; 5.131.388 comparecimentos; 1.051.980 abstenções; zero falhas em `aptos = comparecimento + abstenções`. A taxa estadual ponderada é `17,0131%`. A taxa municipal mínima é `10,35%`, a média simples é `18,71%`, a mediana é `18,51%` e a máxima é `28,92%`.

## Socioeconômico

Fonte consolidada consumida: `data/csv_SIDRA_indicadores_socio_economicos/indicadores_socioeconomicos_paraiba.csv`.

Schema comum: `indicador`, `ano`, `nivel_territorial`, `codigo_localidade`, `localidade`, `variavel`, `unidade`, `valor`, `classificacao`, `categoria`.

O arquivo tem 5.824 linhas e cobre os 223 municípios. Os CSVs menores na mesma pasta preservam cada indicador separadamente.

| Indicador | Ano | Linhas | Organização |
| --- | --- | --- | --- |
| renda média domiciliar per capita | 2022 | 224 | 1 PB + 223 municípios |
| renda mediana domiciliar per capita | 2022 | 224 | 1 PB + 223 municípios |
| distribuição por faixas de moradores | 2022 | 2.688 | 224 territórios x 12 categorias |
| percentual por faixas de moradores | 2022 | 2.688 | 224 territórios x 12 categorias |

Os percentuais municipais por faixa, sem a categoria `Total`, somam entre `99,95%` e `100,09%`. O pipeline aceita somente o intervalo `99,9%` a `100,1%` para absorver arredondamento da fonte. O marcador SIDRA `-` é convertido para `0`, conforme a convenção oficial de zero absoluto.

## Ingestão SIDRA

Configuração: `config/sidra.json`. Ingestor: `pipeline/ingest_sidra.py`.

| Tabela SIDRA | Uso |
| --- | --- |
| `10295` | renda média e mediana domiciliar per capita de 2022 |
| `10296` | distribuição e percentual de moradores por faixas de renda domiciliar per capita de 2022 |

Cada execução preserva JSONs brutos comprimidos e manifesto em `data/raw/ibge/<timestamp>/`.

## Ponte territorial

Não há crosswalk oficial local TSE-IBGE. O pipeline normaliza nomes apenas para construir uma ponte local auditável. Depois disso, o mart usa os códigos persistidos como chaves. Resultado atual: 223 correspondências e zero municípios sem renda local.
