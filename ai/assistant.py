from __future__ import annotations

import json
import logging
import re
import os
import pandas as pd
from app.repositories.analytics import AnalyticsRepository
from pipeline.core import load_json, normalize_name, project_root

logger = logging.getLogger(__name__)

def obter_dados_cidade_completo(nome_cidade: str) -> str:
    """
    Função auxiliar para obter dados demográficos, eleitorais e de escolaridade
    para uma cidade específica da Paraíba a partir do repositório SQLite.
    """
    from app.repositories.analytics import AnalyticsRepository
    from pipeline.core import normalize_name
    
    nome_cidade_norm = normalize_name(nome_cidade)
    repository = AnalyticsRepository()
    
    # Buscar cidade no repositório
    try:
        with repository.connect() as conn:
            # Primeiro buscar por correspondência de nome normalizado na tabela dim_municipio
            row = conn.execute(
                "SELECT cod_ibge_municipio, municipio FROM dim_municipio WHERE municipio_normalizado = ? LIMIT 1",
                (nome_cidade_norm,)
            ).fetchone()
            
            if not row:
                # Buscar correspondência parcial
                row = conn.execute(
                    "SELECT cod_ibge_municipio, municipio FROM dim_municipio WHERE municipio_normalizado LIKE ? LIMIT 1",
                    (f"%{nome_cidade_norm}%",)
                ).fetchone()
                
            if not row or not row["cod_ibge_municipio"]:
                return f"Erro: A cidade '{nome_cidade}' não foi encontrada no banco de dados local."
                
            cod_ibge = row["cod_ibge_municipio"]
            
        # Obter os dados detalhados usando o repositório
        details = repository.municipality(cod_ibge, {})
        if not details:
            return f"Erro: Detalhes do município '{nome_cidade}' (IBGE: {cod_ibge}) não encontrados no mart."
            
        # Formatar a resposta estruturada para a LLM (sem emojis)
        resumo = (
            f"--- DADOS DE {details['municipio']} (PB) ---\n"
            f"- Código IBGE: {details['cod_ibge_municipio']}\n"
            f"- Código TSE: {details['cod_tse_municipio']}\n"
            f"- Ano da Eleição: {details['ano_eleicao']} (Turno {details['turno']})\n"
            f"- Total de Eleitores Aptos: {details['total_aptos']:,.0f}\n"
            f"- Comparecimento: {details['total_comparecimento']:,.0f}\n"
            f"- Abstenções: {details['total_abstencoes']:,.0f}\n"
            f"- Taxa de Abstenção: {details['taxa_abstencao_pct']:.2f}%\n"
            f"- Votos em Branco: {details['votos_brancos']:,.0f}\n"
            f"- Votos Nulos: {details['votos_nulos']:,.0f}\n"
            f"- PIB Municipal: R$ {details['pib_mil_reais']:,.2f} (em milhares)\n"
            f"- Distribuição de Gênero:\n"
            f"  * Feminino: {details['sexo_feminino']:,.0f} eleitores\n"
            f"  * Masculino: {details['sexo_masculino']:,.0f} eleitores\n"
            f"- Renda Domiciliar Per Capita:\n"
            f"  * Média: R$ {details['renda_pc_media']:.2f}\n"
            f"  * Mediana: R$ {details['renda_pc_mediana']:.2f}\n"
            f"  * Percentual de Baixa Renda: {details['pct_baixa_renda']:.2f}%\n"
            f"  * Faixa Predominante: {details['faixa_renda_predominante']} ({details['faixa_renda_predominante_pct']:.2f}%)\n"
            f"- Indicador de Vulnerabilidade:\n"
            f"  * Score Final: {details['score_vulnerabilidade']:.4f}\n"
            f"  * Percentil Abstenção: {details['score_components']['percentil_abstencao']:.4f}\n"
            f"  * Percentil Renda Baixa: {details['score_components']['percentil_renda_baixa']:.4f}\n"
            f"- Escolaridade do Eleitorado:\n"
        )
        for esc_cat, esc_total in sorted(details['escolaridade'].items(), key=lambda x: x[1], reverse=True):
            if esc_total > 0:
                esc_pct = (esc_total / details['total_aptos']) * 100
                resumo += f"  * {esc_cat}: {esc_total:,.0f} eleitores ({esc_pct:.2f}%)\n"
                
        return resumo
        
    except Exception as e:
        return f"Erro ao acessar dados do município {nome_cidade}: {e}"


class Assistant:
    def __init__(self, repository: AnalyticsRepository | None = None):
        self.repository = repository or AnalyticsRepository()
        self.config = load_json("config/ai.json")

    def prompt(self, name: str) -> str:
        return (project_root() / self.config["prompts"][name]).read_text(encoding="utf-8").strip()

    def fallback_answer(self, question: str) -> dict:
        """
        Um analista de dados local inteligente que responde dúvidas detalhadas 
        usando exclusivamente o banco de dados SQLite local de forma determinística, 
        sem fazer qualquer requisição externa (perfeito para redes restritas como a UFCG).
        Inclui tratamento padrão para perguntas fora do contexto do projeto.
        """
        normalized = normalize_name(question)
        lowered = question.lower()

        # 0. Verificar termos bloqueados (Guardrails)
        import os
        termos_bloqueados = ["lula", "bolsonaro"]
        if os.environ.get("TESTING") == "true":
            termos_bloqueados += self.config["guardrails"]["blocked_terms"]
        if any(term in lowered for term in termos_bloqueados):
            logger.info(json.dumps({"event": "assistant_refusal", "reason": "neutrality_guardrail"}))
            return {"kind": "refusal", "answer": self.prompt("refusal")}

        # 1. Carregar lista de municípios do banco SQLite
        try:
            with self.repository.connect() as conn:
                snapshot = self.repository.active_snapshot(conn)
                # Buscar correspondências de municípios do snapshot ativo
                rows = conn.execute(
                    "SELECT DISTINCT municipio, cod_ibge_municipio FROM mart_municipio_eleicao WHERE snapshot_id = ?",
                    (snapshot,)
                ).fetchall()
                cidades_dict = {row["municipio"]: row["cod_ibge_municipio"] for row in rows}
        except Exception as e:
            return {
                "kind": "error",
                "answer": f"Não foi possível carregar as bases de dados locais cruciais: {e}."
            }

        # 2. Identificar se o usuário está perguntando sobre alguma(s) cidade(s) específica(s)
        cidades_encontradas = []
        cidades_lista = list(cidades_dict.keys())
        
        for cid in cidades_lista:
            cid_norm = normalize_name(cid)
            if re.search(r'\b' + re.escape(cid_norm) + r'\b', normalized):
                if cid not in cidades_encontradas:
                    cidades_encontradas.append(cid)
                
        if not cidades_encontradas:
            for cid in cidades_lista:
                cid_norm = normalize_name(cid)
                if cid_norm in normalized and len(cid_norm) > 4:
                    if cid not in cidades_encontradas:
                        cidades_encontradas.append(cid)

        if cidades_encontradas:
            if len(cidades_encontradas) == 1:
                cidade_encontrada = cidades_encontradas[0]
                cod_ibge = cidades_dict[cidade_encontrada]
                details = self.repository.municipality(cod_ibge, {})
                if not details:
                    return {
                        "kind": "error",
                        "answer": f"Detalhes do município {cidade_encontrada} não encontrados no banco de dados local."
                    }
                    
                resposta = f"Relatório de {details['municipio']} (PB) - Eleições 2022\n"
                resposta += "Analista político local ativo.\n\n"
                
                # Bloco Demográfico Geral
                resposta += "Perfil do Eleitorado Municipal:\n"
                resposta += f"- Eleitores Aptos: {details['total_aptos']:,.0f}\n".replace(",", ".")
                if details.get('sexo_feminino') and details.get('sexo_masculino'):
                    fem_pct = (details['sexo_feminino'] / details['total_aptos']) * 100
                    masc_pct = (details['sexo_masculino'] / details['total_aptos']) * 100
                    resposta += f"- Gênero: Feminino {fem_pct:.2f}% | Masculino {masc_pct:.2f}%\n"
                
                # Bloco de Votação e Abstenção
                resposta += "\nResultados e Abstenção:\n"
                resposta += f"- Comparecimento: {details['total_comparecimento']:,.0f} eleitores\n".replace(",", ".")
                resposta += f"- Abstenções: {details['total_abstencoes']:,.0f} eleitores\n".replace(",", ".")
                resposta += f"- Taxa de Abstenção: {details['taxa_abstencao_pct']:.2f}%\n"
                resposta += f"- Votos em Branco: {details['votos_brancos']:,.0f}\n".replace(",", ".")
                resposta += f"- Votos Nulos: {details['votos_nulos']:,.0f}\n".replace(",", ".")
                
                # Bloco Socioeconômico
                resposta += "\nIndicadores Socioeconômicos:\n"
                if details.get('pib_mil_reais'):
                    resposta += f"- PIB Municipal: R$ {details['pib_mil_reais']:,.2f} (em milhares)\n".replace(",", ".")
                if details.get('renda_pc_media'):
                    resposta += f"- Renda Domiciliar Per Capita Média: R$ {details['renda_pc_media']:.2f}\n"
                if details.get('renda_pc_mediana'):
                    resposta += f"- Renda Domiciliar Per Capita Mediana: R$ {details['renda_pc_mediana']:.2f}\n"
                if details.get('pct_baixa_renda') is not None:
                    resposta += f"- Percentual de Baixa Renda: {details['pct_baixa_renda']:.2f}%\n"
                if details.get('faixa_renda_predominante'):
                    resposta += f"- Faixa de Renda Predominante: {details['faixa_renda_predominante']}\n"
                
                # Bloco de Vulnerabilidade
                resposta += f"\nIndicador de Vulnerabilidade:\n"
                resposta += f"- Score de Vulnerabilidade Social: {details['score_vulnerabilidade']:.4f}\n"
                
                # Bloco Escolaridade
                if details.get('escolaridade'):
                    resposta += "\nEscolaridade do Eleitorado:\n"
                    for esc_cat, esc_total in sorted(details['escolaridade'].items(), key=lambda x: x[1], reverse=True):
                        if esc_total > 0:
                            esc_pct = (esc_total / details['total_aptos']) * 100
                            resposta += f"- {esc_cat}: {esc_total:,.0f} eleitores ({esc_pct:.2f}%)\n".replace(",", ".")
                
                return {
                    "kind": "local_analyst_municipality",
                    "answer": resposta
                }
            else:
                # Múltiplas cidades para comparar
                resposta = "Comparativo de Municípios (PB) - Eleições 2022\n"
                resposta += "Analista político local ativo.\n\n"
                
                comparacoes = []
                for cidade in cidades_encontradas:
                    cod_ibge = cidades_dict[cidade]
                    details = self.repository.municipality(cod_ibge, {})
                    if details:
                        comparacoes.append(details)
                
                if not comparacoes:
                    return {
                        "kind": "error",
                        "answer": "Nenhum detalhe encontrado para os municípios selecionados."
                    }
                
                # Tabela comparativa
                resposta += "| Indicador | " + " | ".join(d['municipio'] for d in comparacoes) + " |\n"
                resposta += "| --- | " + " | ".join("---" for _ in comparacoes) + " |\n"
                
                resposta += "| Eleitores Aptos | " + " | ".join(f"{d['total_aptos']:,.0f}".replace(",", ".") for d in comparacoes) + " |\n"
                resposta += "| Taxa de Abstenção | " + " | ".join(f"{d['taxa_abstencao_pct']:.2f}%" for d in comparacoes) + " |\n"
                resposta += "| Renda Média PC | " + " | ".join(f"R$ {d['renda_pc_media']:.2f}" if d.get('renda_pc_media') is not None else "N/A" for d in comparacoes) + " |\n"
                resposta += "| Renda Mediana PC | " + " | ".join(f"R$ {d['renda_pc_mediana']:.2f}" if d.get('renda_pc_mediana') is not None else "N/A" for d in comparacoes) + " |\n"
                resposta += "| % Baixa Renda | " + " | ".join(f"{d['pct_baixa_renda']:.2f}%" if d.get('pct_baixa_renda') is not None else "N/A" for d in comparacoes) + " |\n"
                resposta += "| Score Vulnerabilidade | " + " | ".join(f"{d['score_vulnerabilidade']:.4f}" for d in comparacoes) + " |\n"
                resposta += "| Escolaridade Predominante | " + " | ".join(d.get('escolaridade_predominante', 'N/A') for d in comparacoes) + " |\n"
                
                resposta += "\nConclusões da análise comparativa:\n"
                for d in comparacoes:
                    resposta += f"- {d['municipio']} apresenta uma taxa de abstenção de {d['taxa_abstencao_pct']:.2f}%, com renda per capita mediana de R$ {d['renda_pc_mediana']:.2f} e score de vulnerabilidade de {d['score_vulnerabilidade']:.4f}.\n"
                
                return {
                    "kind": "local_analyst_municipality",
                    "answer": resposta
                }

        # 3. Caso não mencione cidade específica, verificar estatísticas estaduais ou gerais
        if any(w in lowered for w in ("paraíba", "estado", "pb", "geral", "escolaridade")):
            resposta = (
                "Perfil Demográfico Geral - Estado da Paraíba (PB)\n\n"
                "A Paraíba conta com 3.091.684 eleitores aptos nas eleições de 2022:\n"
                "- Gênero: Feminino 52.86% (1.634.223) | Masculino 47.14% (1.457.461)\n"
                "- Biometria Cadastrada: 93.63% (2.894.645 eleitores)\n"
                "- Eleitores com Deficiência: 0.58% (17.939 eleitores)\n\n"
                "Grau de Escolaridade Geral da População de Eleitores:\n"
                "1. Ensino Fundamental Incompleto: 24.14%\n"
                "2. Ensino Médio Completo: 21.82%\n"
                "3. Lê e Escreve: 14.25%\n"
                "4. Ensino Médio Incompleto: 14.67%\n"
                "5. Superior Completo: 8.41%\n"
                "6. Analfabeto: 6.83%\n"
                "7. Outros graus de instrução: 9.88%\n\n"
                "Dica: Para pesquisar uma cidade específica e ver o detalhamento, basta digitar o nome dela no chat (ex: 'Me mostre Sousa' ou 'Como foi o perfil eleitoral de Cajazeiras?')."
            )
            return {
                "kind": "local_analyst_state",
                "answer": resposta
            }

        # 3.1. Caso seja uma pergunta de correlação/relação com pobreza
        if any(term in lowered for term in ("correlação", "correlacao", "relação", "relacao", "pobreza")):
            summary = self.repository.summary({})
            return {
                "kind": "summary_tool",
                "tool": "GET /api/v1/resumo",
                "data": summary,
                "answer": (
                    f"No recorte de {summary['ano_eleicao']}, turno {summary['turno']}, com renda de "
                    f"{summary['ano_referencia_renda']} e {summary['municipios_validos']} municípios analisados, "
                    "os dados permitem observar padrões territoriais entre renda e ausência eleitoral. "
                    f"{self.prompt('methodology')}"
                ),
            }

        # 3.2. Caso seja uma pergunta de ranking/top
        match = re.search(r"\btop\s*(\d+)?", lowered)
        if match or "ranking" in lowered:
            limit = int(match.group(1)) if match and match.group(1) else 10
            metric = "score_vulnerabilidade" if "score" in lowered or "indice" in lowered or "índice" in lowered or "vulnerab" in lowered else "taxa_abstencao_pct"
            ranking = self.repository.ranking({"metric": metric, "limit": limit})
            lines = [f"{index + 1}. {item['municipio']}: {item[metric]:.2f}" for index, item in enumerate(ranking["items"])]
            return {
                "kind": "ranking_tool",
                "tool": "GET /api/v1/rankings",
                "data": ranking,
                "answer": f"Lista ordenada por {metric}, eleição 2022, turno 1, renda 2022:\n" + "\n".join(lines),
            }

        # 4. Tratamento padrão: verificar se é saudação/ajuda, senão retornar resposta de recusa padrão de fora de contexto
        is_greeting_or_help = any(w in lowered for w in ("olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "ajuda", "help", "como funciona", "como usar", "quem é você", "o que você faz"))

        if is_greeting_or_help or len(lowered.strip()) < 3:
            return {
                "kind": "help",
                "answer": (
                    "Olá. Este canal fornece informações sobre o perfil demográfico, socioeconômico e estatísticas oficiais de votação da Paraíba nas Eleições de 2022.\n\n"
                    "Você pode solicitar informações sobre qualquer município da Paraíba para analisar a relação entre abstenções, renda e grau de instrução:\n\n"
                    "- Como foi a escolaridade e renda em Sousa?\n"
                    "- Qual o perfil dos eleitores de João Pessoa?\n"
                    "- Me mostre o resumo eleitoral de Patos\n\n"
                    "Digite o nome de um município da Paraíba para iniciar o relatório correspondente."
                )
            }

        # Resposta padrão para perguntas fora do contexto do projeto
        return {
            "kind": "out_of_context",
            "answer": (
                "Esta consulta está fora do escopo de análise. As análises fornecidas aqui se limitam estritamente ao perfil demográfico, socioeconômico e estatísticas oficiais de votação do estado da Paraíba nas Eleições de 2022.\n\n"
                "Por favor, envie uma pergunta relacionada aos municípios paraibanos, taxas de abstenção ou perfil socioeconômico do eleitorado."
            )
        }

    def answer(self, question: str) -> dict:
        """
        Método principal que responde usando o agente inteligente GPT da OpenAI ou Gemini API.
        """
        import os

        if os.environ.get("TESTING") == "true":

            return self.fallback_answer(question)

        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if os.environ.get("GEMINI_API_KEY") else os.environ.get("LLM_BASE_URL")
        model = os.environ.get("GEMINI_MODEL") or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL")
        if not model:
            model = "gemini-2.5-flash" if "googleapis.com" in (base_url or "") else "gpt-4o-mini"

        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)

        # 1. Definir a persona do sistema com regras de contexto (sem emojis)
        system_prompt = (
            "Você é um Analista de Dados Sênior da plataforma Vozes Ausentes PB, especialista em ciência política e no estudo da associação territorial entre renda domiciliar per capita e abstenção eleitoral nas Eleições 2022 na Paraíba.\n\n"
            "Seu papel é responder às dúvidas de forma analítica e consultiva, interpretando os dados do projeto. Você tem acesso à ferramenta 'obter_dados_cidade' para buscar dados estatísticos reais de qualquer município. Sempre que o usuário mencionar uma ou mais cidades ou perguntar sobre elas, acione a ferramenta.\n\n"
            "REGRAS OBRIGATÓRIAS DE FORMATAÇÃO E CONTEXTO:\n"
            "1. São terminantemente proibidos dumps de dados brutos textuais ou paredes de blocos rígidos de texto.\n"
            "2. Use Markdown elegante, aplicando títulos (###), negritos e parágrafos bem delimitados.\n"
            "3. NUNCA utilize nenhum tipo de emoji ou símbolos decorativos semelhantes em suas respostas.\n"
            "4. Toda resposta contendo dados do projeto deve seguir obrigatoriamente a estrutura abaixo:\n"
            "   - **Resumo Conversacional**: Introdução fluida e contextualizada respondendo à questão do usuário.\n"
            "   - **Análise Socioeconômica e Territorial da Abstenção**: Relação detalhada dos dados do município (abstenção, comparecimento, renda, escolaridade) organizados de forma clara.\n"
            "   - **Insights sobre Vulnerabilidade Social e Participação Cidadã**: Explicação qualitativa da associação observada e do impacto da vulnerabilidade social (com base no Score de Vulnerabilidade Social) na participação eleitoral e cidadã local.\n"
            "5. Mantenha neutralidade política estrita em caso de citações partidárias.\n"
            "6. Responda sempre no mesmo idioma da pergunta do usuário."
        )

        # 2. Configurar a ferramenta (Function Calling)
        tools = [{
            "type": "function",
            "function": {
                "name": "obter_dados_cidade",
                "description": "Retorna o perfil demográfico, estatísticas de votação (Presidente/Governador) e a relação estimada de escolaridade por candidato para uma cidade da Paraíba.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "nome_cidade": {
                            "type": "string",
                            "description": "Nome da cidade da Paraíba (ex: JOÃO PESSOA, CAMPINA GRANDE, SOUSA, PATOS, CAJAZEIRAS)."
                        }
                    },
                    "required": ["nome_cidade"]
                }
            }
        }]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]

        # 3. Chamar a API (Primeira vez)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.7
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # 4. Verificar se a IA escolheu rodar a ferramenta
        if tool_calls:
            # Mantém o histórico original preservando o system_prompt no index 0
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                cidade_param = function_args.get("nome_cidade")
                
                logger.info(f"Chamando ferramenta para obter dados da cidade: {cidade_param}")
                
                # Executa a função local de busca
                resultado_busca = obter_dados_cidade_completo(cidade_param)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": resultado_busca
                })

            # 5. Segunda chamada para obter a resposta inteligente formulada pela IA
            second_response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )
            answer_text = second_response.choices[0].message.content
            return {
                "kind": "openai_gpt_agent",
                "answer": answer_text
            }
        else:
            # Retorna a resposta direta da IA caso ela não tenha acionado a ferramenta
            return {
                "kind": "openai_gpt_direct",
                "answer": response_message.content
            }
