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
    por candidato para uma cidade específica da Paraíba.
    """
    nome_cidade = nome_cidade.strip().upper()
    
    # 1. Carregar os CSVs gerados pelo script geral_eleitores_pb.py
    try:
        df_dem = pd.read_csv('perfil_demografico_municipios_pb_2022.csv', sep=';')
        df_votos = pd.read_csv('resultado_consolidado_municipios_pb_2022.csv', sep=';')
    except Exception as e:
        return f"Erro ao carregar arquivos de dados eleitorais locais: {e}"
        
    cidades_dem = df_dem[df_dem['NM_MUNICIPIO'].str.upper() == nome_cidade]
    if cidades_dem.empty:
        sugestoes = df_dem[df_dem['NM_MUNICIPIO'].str.upper().str.contains(nome_cidade, na=False)]['NM_MUNICIPIO'].tolist()
        sugest_str = f" Você quis dizer: {', '.join(sugestoes[:3])}?" if sugestoes else ""
        return f"Erro: A cidade '{nome_cidade}' não foi encontrada no banco demográfico da PB.{sugest_str}"
        
    row_dem = cidades_dem.iloc[0]
    cid_cod = row_dem['CD_MUNICIPIO']
    
    # Bloco Demográfico Geral do Município
    dem_info = (
        f"--- DADOS DEMOGRÁFICOS DE {row_dem['NM_MUNICIPIO']} (PB) ---\n"
        f"- Total de Eleitores Aptos: {row_dem['TOTAL_ELEITORES']:,.0f}\n"
        f"- Biometria Cadastrada: {row_dem['BIOMETRIA_PCT']:.2f}%\n"
        f"- Eleitores com Deficiência: {row_dem['DEFICIENCIA_PCT']:.2f}%\n"
        f"- Gênero Feminino: {row_dem['GENERO_FEMININO_PCT']:.2f}%\n"
        f"- Gênero Masculino: {row_dem['GENERO_MASCULINO_PCT']:.2f}%\n"
        f"- Distribuição Geral de Escolaridade:\n"
    )
    edu_cols = [c for c in df_dem.columns if c.startswith('ESCOLARIDADE_')]
    edu_vals = {c.replace('ESCOLARIDADE_', '').replace('_PCT', ''): row_dem[c] for c in edu_cols}
    for edu_cat, edu_val in sorted(edu_vals.items(), key=lambda x: x[1], reverse=True):
        if edu_val > 0:
            dem_info += f"  * {edu_cat}: {edu_val:.2f}%\n"
            
    # Bloco de Apuração de Votos do Município (1º Turno 2022)
    row_v = df_votos[df_votos['CD_MUNICIPIO'] == cid_cod]
    votes_info = ""
    if not row_v.empty:
        r_v = row_v.iloc[0]
        votes_info = (
            f"\n--- APURAÇÃO DE VOTOS (1º TURNO 2022) ---\n"
            f"VOTAÇÃO PARA PRESIDENTE DA REPÚBLICA:\n"
            f"- Comparecimento: {r_v['PRES_COMPARECIMENTO']:,.0f} | Abstenções: {r_v['PRES_ABSTENCOES']:,.0f}\n"
            f"- Votos em Branco: {r_v['PRES_VOTOS_BRANCOS']:,.0f} | Votos Nulos: {r_v['PRES_VOTOS_NULOS']:,.0f}\n"
            f"- Votos por Candidato:\n"
        )
        pres_cols = [c for c in df_votos.columns if c.startswith('PRES_VOTOS_') and c not in ['PRES_VOTOS_BRANCOS', 'PRES_VOTOS_NULOS']]
        pres_votes = {c.replace('PRES_VOTOS_', ''): r_v[c] for c in pres_cols if r_v[c] > 0}
        for cand, votos in sorted(pres_votes.items(), key=lambda x: x[1], reverse=True):
            votes_info += f"  * {cand}: {votos:,.0f} votos\n"
            
        votes_info += (
            f"\nVOTAÇÃO PARA GOVERNADOR DO ESTADO:\n"
            f"- Comparecimento: {r_v['GOV_COMPARECIMENTO']:,.0f} | Abstenções: {r_v['GOV_ABSTENCOES']:,.0f}\n"
            f"- Votos em Branco: {r_v['GOV_VOTOS_BRANCOS']:,.0f} | Votos Nulos: {r_v['GOV_VOTOS_NULOS']:,.0f}\n"
            f"- Votos por Candidato:\n"
        )
        gov_cols = [c for c in df_votos.columns if c.startswith('GOV_VOTOS_') and c not in ['GOV_VOTOS_BRANCOS', 'GOV_VOTOS_NULOS']]
        gov_votes = {c.replace('GOV_VOTOS_', ''): r_v[c] for c in gov_cols if r_v[c] > 0}
        for cand, votos in sorted(gov_votes.items(), key=lambda x: x[1], reverse=True):
            votes_info += f"  * {cand}: {votos:,.0f} votos\n"

    # Bloco de Escolaridade Estimada dos Votantes de cada Candidato
    edu_cand_info = ""
    try:
        df_edu_pres = pd.read_csv('resultado_presidente_escolaridade_municipios_pb_2022.csv', sep=';')
        df_edu_gov = pd.read_csv('resultado_governador_escolaridade_municipios_pb_2022.csv', sep=';')
        
        df_ep_cid = df_edu_pres[df_edu_pres['CD_MUNICIPIO'] == cid_cod]
        df_eg_cid = df_edu_gov[df_edu_gov['CD_MUNICIPIO'] == cid_cod]
        
        if not df_ep_cid.empty:
            edu_cand_info += "\n--- RELAÇÃO ESTIMADA DE GRAU DE ESCOLARIDADE POR CANDIDATO A PRESIDENTE ---\n"
            top_pres = df_ep_cid.groupby('NM_URNA_CANDIDATO')['TOTAL_ESTIMATED'].first().nlargest(4).index.tolist()
            for cand in top_pres:
                edu_cand_info += f"Candidato: {cand} (Total Estimado: {df_ep_cid[df_ep_cid['NM_URNA_CANDIDATO'] == cand]['TOTAL_ESTIMATED'].iloc[0]:,.0f} votos)\n"
                df_c = df_ep_cid[df_ep_cid['NM_URNA_CANDIDATO'] == cand].sort_values(by='PCT', ascending=False)
                for _, r in df_c.iterrows():
                    if r['PCT'] > 0:
                        edu_cand_info += f"  * {r['DS_GRAU_ESCOLARIDADE']}: {r['PCT']:.2f}%\n"
                        
        if not df_eg_cid.empty:
            edu_cand_info += "\n--- RELAÇÃO ESTIMADA DE GRAU DE ESCOLARIDADE POR CANDIDATO A GOVERNADOR ---\n"
            top_gov = df_eg_cid.groupby('NM_URNA_CANDIDATO')['TOTAL_ESTIMATED'].first().nlargest(4).index.tolist()
            for cand in top_gov:
                edu_cand_info += f"Candidato: {cand} (Total Estimado: {df_eg_cid[df_eg_cid['NM_URNA_CANDIDATO'] == cand]['TOTAL_ESTIMATED'].iloc[0]:,.0f} votos)\n"
                df_c = df_eg_cid[df_eg_cid['NM_URNA_CANDIDATO'] == cand].sort_values(by='PCT', ascending=False)
                for _, r in df_c.iterrows():
                    if r['PCT'] > 0:
                        edu_cand_info += f"  * {r['DS_GRAU_ESCOLARIDADE']}: {r['PCT']:.2f}%\n"
    except Exception as e:
        edu_cand_info = f"\n(Nota: Relação de escolaridade de candidatos indisponível: {e})"
        
    return dem_info + votes_info + edu_cand_info


class Assistant:
    def __init__(self, repository: AnalyticsRepository | None = None):
        self.repository = repository or AnalyticsRepository()
        self.config = load_json("config/ai.json")

    def prompt(self, name: str) -> str:
        return (project_root() / self.config["prompts"][name]).read_text(encoding="utf-8").strip()

    def fallback_answer(self, question: str) -> dict:
        """
        Fallback baseado em regras locais e correspondência de palavras-chave 
        para quando a API da OpenAI não estiver configurada ou falhar.
        """
        normalized = normalize_name(question)
        lowered = question.lower()
        if any(term in lowered for term in self.config["guardrails"]["blocked_terms"]):
            logger.info(json.dumps({"event": "assistant_refusal", "reason": "neutrality_guardrail"}))
            return {"kind": "refusal", "answer": self.prompt("refusal")}
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
        municipalities = self.repository.list_municipalities({"page_size": self.repository.config["api"]["max_page_size"]})["items"]
        for item in municipalities:
            if normalize_name(item["municipio"]) in normalized:
                detail = self.repository.municipality(item["cod_ibge_municipio"], {})
                return {
                    "kind": "municipality_tool",
                    "tool": "GET /api/v1/municipios/{cod_ibge}",
                    "data": detail,
                    "answer": (
                        f"{detail['municipio']}: taxa de abstenção de {detail['taxa_abstencao_pct']:.2f}% "
                        f"na eleição de {detail['ano_eleicao']}, turno {detail['turno']}; renda mediana per capita "
                        f"de R$ {detail['renda_pc_mediana']:.2f} em {detail['ano_referencia_renda']}; "
                        f"índice de atenção {detail['score_vulnerabilidade']:.2f}/100."
                    ),
                }
        return {
            "kind": "help",
            "answer": self.prompt("help"),
        }

    def answer(self, question: str) -> dict:
        """
        Método principal que responde usando o agente inteligente GPT da OpenAI (Opção 3).
        Caso a chave da API não esteja configurada ou ocorra algum erro, recorre automaticamente
        ao fallback local robusto.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY não encontrada no ambiente. Utilizando fallback local.")
            return self.fallback_answer(question)

        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)

            # 1. Definir a persona do sistema
            system_prompt = (
                "Você é um cientista político especialista em eleições e no perfil do eleitorado do estado da Paraíba (PB).\n"
                "Seu papel é responder às dúvidas dos usuários de forma inteligente, crítica e politicamente analítica.\n"
                "Você tem acesso à ferramenta 'obter_dados_cidade' para obter estatísticas reais de qualquer município da Paraíba. "
                "SEMPRE que o usuário mencionar uma cidade ou perguntar sobre ela, use a ferramenta para buscar os dados correspondentes.\n"
                "Ao analisar os dados obtidos:\n"
                "- Identifique quem venceu para Presidente e Governador na cidade.\n"
                "- Analise as abstenções, votos nulos e brancos.\n"
                "- Relacione de forma crítica os resultados dos candidatos com o grau de escolaridade dos eleitores "
                "(ex: a porcentagem de analfabetos ou pessoas com ensino superior completo que votaram em cada candidato).\n"
                "Responda sempre em português brasileiro de forma clara e fluida, formatando a resposta de maneira elegante usando markdown."
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

            # 3. Chamar a OpenAI (Primeira vez)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # 4. Verificar se a IA escolheu rodar a ferramenta
            if tool_calls:
                messages.append(response_message)
                
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    cidade_param = function_args.get("nome_cidade")
                    
                    logger.info(f"Chatbot inteligente chamando ferramenta para obter dados da cidade: {cidade_param}")
                    
                    # Executa a função local de busca
                    resultado_busca = obter_dados_cidade_completo(cidade_param)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": resultado_busca
                    })

                # 5. Segunda chamada para obter a resposta inteligente formulada pela IA
                second_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages
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

        except Exception as e:
            logger.error(f"Erro na comunicação com a API da OpenAI: {e}. Executando fallback.")
            return self.fallback_answer(question)
