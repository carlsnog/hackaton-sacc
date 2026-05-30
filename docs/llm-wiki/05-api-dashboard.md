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

No mart completo: 223 municípios; taxa ponderada de abstenção `17,0131%`. Os 223 municípios abrangem `100%` do território e dos 3.225.826 eleitores aptos informados para a Paraíba. O arquivo eleitoral local preserva somas agregadas próprias para o cálculo auditável da taxa; essas somas não são exibidas como contagem de eleitores únicos.

O dashboard apresenta cartões explicativos, mapa de calor, dispersão com escalas visíveis, tabela ordenável e grupos por faixa predominante. O mapa usa `data/geo/geojs-25-mun.json`, que contém polígonos para os 223 municípios. Todos são coloridos pela taxa de abstenção.
