# IA, prompts e credenciais

## Funcionamento atual

O assistente usa roteamento determinístico em `ai/assistant.py`. Perguntas de ranking acionam o repositório de ranking; nomes de municípios acionam detalhe; perguntas sobre pobreza ou correlação acionam resumo; pedidos incompatíveis com neutralidade recebem recusa.

Isso garante respostas quantitativas rastreáveis mesmo sem provedor externo. Hoje não existe uma chamada a LLM: a resposta final é montada por templates locais após a execução da consulta analítica.

Fluxo atual:

```text
pergunta -> guardrails -> identificação da intenção -> repository SQL -> template local -> resposta
```

## Prompts editáveis

| Arquivo | Papel |
| --- | --- |
| `ai/prompts/system.txt` | comportamento geral |
| `ai/prompts/methodology.txt` | ressalvas interpretativas |
| `ai/prompts/refusal.txt` | texto de recusa |
| `ai/prompts/help.txt` | orientação exibida para consultas não reconhecidas |

Os caminhos ficam em `config/ai.json`, portanto prompts alternativos podem ser ativados sem mudar código.

## Chaves

`config/ai.json` contém somente os nomes das variáveis: `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL`. Valores reais pertencem ao ambiente local e nunca ao repositório. `.env.example` documenta os nomes.

O provedor está configurado como `disabled`.

## Documentos RAG

Cada documento municipal contém metadados temporais, versão do score, taxa, delta contra o recorte ponderado, renda, percentuais por faixa, componentes do score e hashes das duas fontes locais. O conteúdo é reconstruído pelo pipeline; não edite `data/rag/` manualmente.

Os JSONs RAG já são produzidos, mas ainda não são recuperados pelo assistente atual.

## Como habilitar uma LLM contextual

1. Criar `ai/providers/openai_compatible.py` como adapter HTTP isolado.
2. Ler `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL` exclusivamente do ambiente.
3. Preservar o roteamento atual para executar SQL antes da chamada ao modelo.
4. Selecionar os JSONs em `data/rag/<snapshot_id>/` somente para os municípios citados ou retornados pela tool.
5. Enviar à LLM: prompts editáveis, pergunta original, resultado estruturado da tool e documentos RAG selecionados.
6. Exigir que a resposta mencione recorte temporal, cobertura e fontes; nunca permitir que o modelo invente cálculos.
7. Testar fallback: se a LLM estiver indisponível, retornar o template determinístico atual.

Fluxo desejado:

```text
pergunta -> guardrails -> tool SQL -> recuperação RAG filtrada -> adapter LLM -> resposta contextual
                                      \-> fallback por template local
```

Para trocar prompts ou nomes de variáveis de credencial, edite somente `config/ai.json`. Para mudar o texto comportamental, edite `ai/prompts/`.
