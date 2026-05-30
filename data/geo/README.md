# Malha municipal da Paraíba

Adicione a malha municipal local em:

```text
data/geo/municipios-pb.geojson
```

O arquivo deve ser um `FeatureCollection` GeoJSON. Cada município deve possuir um código IBGE em uma destas propriedades: `cod_ibge_municipio`, `CD_MUN`, `CD_GEOCMU`, `id`; também é aceito `feature.id`.

O dashboard do Vozes Ausentes PB carregará o arquivo automaticamente pela rota `GET /api/v1/geojson` e colorirá os municípios pela taxa de abstenção disponível.
