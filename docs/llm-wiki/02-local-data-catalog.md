# Catálogo dos dados locais

## Eleitoral

Arquivo: `data/abstencao_nulos_brancos_2022_pb.csv`.

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

O arquivo tem 220 linhas: 200 municipais e 20 estaduais. Há 10 municípios. Os CSVs menores na mesma pasta são recortes equivalentes preservados para auditoria.

| Indicador | Ano | Linhas | Organização |
| --- | --- | --- | --- |
| renda média domiciliar per capita | 2022 | 11 | 1 PB + 10 municípios |
| renda mediana domiciliar per capita | 2022 | 11 | 1 PB + 10 municípios |
| distribuição por faixas | 2010 | 99 | 11 territórios x 9 categorias |
| percentual por faixas | 2010 | 99 | 11 territórios x 9 categorias |

Os percentuais municipais por faixa, sem a categoria `Total`, somam entre `99,98%` e `100,01%`. O pipeline aceita somente o intervalo `99,9%` a `100,1%` para absorver arredondamento da fonte.

## Ponte territorial

Não há crosswalk oficial local TSE-IBGE. O pipeline normaliza nomes apenas para construir uma ponte local auditável. Depois disso, o mart usa os códigos persistidos como chaves. Resultado: 10 correspondências e 213 municípios sem renda local.
