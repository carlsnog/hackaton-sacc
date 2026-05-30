# API e dashboard

Suba o servidor com `make serve` e abra `http://localhost:8000`.

## Rotas

| Rota | Uso |
| --- | --- |
| `GET /health` | API, banco e última execução |
| `GET /api/v1/status` | última execução do pipeline |
| `GET /api/v1/resumo` | totais ponderados e correlações |
| `GET /api/v1/municipios` | lista paginada, busca e ordenação |
| `GET /api/v1/municipios/{cod_ibge}` | detalhe e delta contra o recorte |
| `GET /api/v1/rankings` | ranking por métrica permitida |
| `GET /api/v1/grupos-renda` | agregação por faixa predominante |
| `GET /api/v1/grupos-renda.csv` | exportação da agregação por faixa predominante |
| `GET /api/v1/export.csv` | exportação UTF-8 com BOM |
| `GET /api/v1/geojson` | malha municipal local, quando disponível |
| `POST /api/v1/assistant` | consulta assistida local |

Filtros temporais: `ano_eleicao`, `turno`, `ano_renda`, `snapshot_id`. Lista: `busca`, `page`, `page_size`, `sort`, `order`. Ranking: `metric`, `limit`, `order`.

## Métricas do snapshot inicial

No mart parcial: 10 municípios; 2.633.570 aptos; 391.223 abstenções; taxa ponderada `14,8552%`. Considerando o total estadual informado de 3.225.826 eleitores aptos, o recorte representa `81,64%` dos eleitores da Paraíba. Pearson (`0,1241`) e Spearman (`0,0365`) continuam disponíveis na API para auditoria, mas não são destacados na interface porque a cobertura local é parcial e os resultados não sustentam uma leitura útil para o público final.

O dashboard apresenta cartões explicativos, mapa de calor, dispersão com escalas visíveis, tabela ordenável e grupos por faixa predominante. O mapa usa `data/geo/geojs-25-mun.json`, que contém polígonos para os 223 municípios. Os 10 municípios com renda cruzada são coloridos pela taxa de abstenção; os demais ficam em cinza.
