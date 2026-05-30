# Limitações conhecidas

## Dados ausentes

- Não há crosswalk oficial TSE-IBGE local. A ponte atual é um fallback auditável por nome normalizado para as 10 cidades com renda.
- Não há malha GeoJSON ou TopoJSON. O componente de mapa de calor está pronto, mas exibe um fallback até que `data/geo/municipios-pb.geojson` seja fornecido.
- Não há dados eleitorais por seção. Deduplicação e auditoria por zona/seção não são executáveis com o CSV atual.
- Não há cobertura socioeconômica para 213 municípios. Rankings e correlações cruzadas representam somente 10 municípios.
- As faixas de renda são de 2010, enquanto renda média/mediana e eleitoral são de 2022.

## Decisões deliberadas

- Nenhuma lacuna foi preenchida por download, estimativa ou fonte externa.
- O SQLite substitui PostgreSQL no MVP executável local. O repository isola a futura troca.
- O assistente não chama LLM externo por padrão. O comportamento quantitativo já funciona via tools locais.

## Próxima ampliação de dados

Quando arquivos locais completos forem adicionados, priorizar: crosswalk oficial, socioeconômico de 223 municípios, malha geográfica e eleitoral por seção. O pipeline deve evoluir preservando os schemas canônicos.
