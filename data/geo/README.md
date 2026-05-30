# Malha municipal da Paraíba

Arquivo consumido pelo dashboard:

```text
data/geo/geojs-25-mun.json
```

## Estrutura validada

- Formato: `FeatureCollection`.
- Cobertura: 223 municípios da Paraíba.
- Geometria: 223 polígonos municipais.
- Chave territorial: `properties.id`, código IBGE de 7 dígitos.
- Exibição: `properties.name`.

O dashboard associa os polígonos ao mart analítico pelo código IBGE. Os 10 municípios com dados socioeconômicos cruzados recebem cor conforme a taxa de abstenção; os demais permanecem em cinza até a ampliação dos dados locais.
