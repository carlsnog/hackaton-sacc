# Vozes Ausentes PB

MVP analítico construído somente com os arquivos locais de `data/`. O sistema preserva a base eleitoral completa, integra o subconjunto socioeconômico disponível, publica snapshots auditáveis e expõe dashboard, API e assistente local orientado por ferramentas.

## Execução

```bash
make pipeline
make test
make serve
```

Abra `http://localhost:8000`. Também é possível executar `podman compose up --build`.

Os alvos do `Makefile` executam pipeline, testes e servidor dentro do Podman. Não é necessário instalar dependências Python no host.

## Configuração

- Regras do pipeline, caminhos e pesos do score: `config/settings.json`.
- Provedor, nomes de variáveis de ambiente e guardrails de IA: `config/ai.json`.
- Comportamento editável do assistente: `ai/prompts/`.
- Credenciais opcionais: variáveis descritas em `.env.example`; nenhuma chave é versionada.

O MVP usa SQLite e a biblioteca padrão do Python para funcionar sem instalação de pacotes. A evolução para PostgreSQL pode substituir o repositório em `app/repositories/` sem alterar os contratos HTTP.

## Cobertura local

O eleitoral contém 223 municípios PB, já agregados. A renda municipal contém 10 municípios; portanto, o mart cruzado e as análises renda-abstenção têm cobertura parcial. O dashboard usa `data/geo/geojs-25-mun.json`, com os polígonos dos 223 municípios, para exibir o mapa de calor. Os municípios sem renda cruzada permanecem em cinza.

Comece a leitura técnica por [`docs/llm-wiki/00-index.md`](docs/llm-wiki/00-index.md). A matriz de entregas e bloqueios locais está em [`docs/llm-wiki/09-requirements-traceability.md`](docs/llm-wiki/09-requirements-traceability.md).
