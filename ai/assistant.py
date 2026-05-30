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
        Um analista de dados local inteligente que responde dúvidas detalhadas 
        usando exclusivamente os CSVs locais de forma determinística, 
        sem fazer qualquer requisição externa (perfeito para redes restritas como a UFCG).
        """
        normalized = normalize_name(question)
        lowered = question.lower()
        
        # 1. Carregar os bancos de dados CSV
        try:
            df_dem = pd.read_csv('perfil_demografico_municipios_pb_2022.csv', sep=';')
            df_votos = pd.read_csv('resultado_consolidado_municipios_pb_2022.csv', sep=';')
            df_edu_pres = pd.read_csv('resultado_presidente_escolaridade_municipios_pb_2022.csv', sep=';')
            df_edu_gov = pd.read_csv('resultado_governador_escolaridade_municipios_pb_2022.csv', sep=';')
        except Exception as e:
            return {
                "kind": "error", 
                "answer": f"### ⚠️ Erro Local\n\nNão foi possível carregar as bases de dados locais cruciais: **{e}**.\n\n*Certifique-se de executar o contêiner ou o script consolidador primeiro.*"
            }

        # 2. Identificar se o usuário está perguntando sobre alguma cidade específica
        cidade_encontrada = None
        cidades_lista = df_dem['NM_MUNICIPIO'].tolist()
        
        # Procura correspondência para cada cidade da lista
        for cid in cidades_lista:
            cid_norm = normalize_name(cid)
            if f" {cid_norm} " in f" {normalized} " or normalized.startswith(cid_norm) or normalized.endswith(cid_norm):
                cidade_encontrada = cid
                break
                
        if not cidade_encontrada:
            for cid in cidades_lista:
                cid_norm = normalize_name(cid)
                if cid_norm in normalized and len(cid_norm) > 4:
                    cidade_encontrada = cid
                    break

        if cidade_encontrada:
            row_dem = df_dem[df_dem['NM_MUNICIPIO'] == cidade_encontrada].iloc[0]
            cid_cod = row_dem['CD_MUNICIPIO']
            
            quer_escolaridade = any(w in lowered for w in ("escolaridade", "grau", "estudo", "ensino", "analfabeto", "superior", "médio", "fundamental"))
            quer_votos = any(w in lowered for w in ("voto", "resultado", "ganhou", "venceu", "candidato", "eleição", "lula", "bolsonaro", "joão", "pedro", "nilvan", "veneziano"))
            
            if not quer_escolaridade and not quer_votos:
                quer_escolaridade = True
                quer_votos = True
                
            resposta = f"### 📊 Relatório de **{cidade_encontrada} (PB)** — Eleições 2022\n"
            resposta += f"*(Analista local inteligente ativo - Sem necessidade de internet/OpenAI)*\n\n"
            
            # Bloco Demográfico Geral
            resposta += "#### 👥 Perfil do Eleitorado Municipal\n"
            resposta += f"- **Eleitores Aptos**: {row_dem['TOTAL_ELEITORES']:,.0f}\n".replace(",", ".")
            resposta += f"- **Biometria**: {row_dem['BIOMETRIA_PCT']:.2f}% dos eleitores cadastrados.\n"
            resposta += f"- **Gênero**: Feminino {row_dem['GENERO_FEMININO_PCT']:.2f}% | Masculino {row_dem['GENERO_MASCULINO_PCT']:.2f}%\n"
            resposta += f"- **Pessoas com Deficiência**: {row_dem['DEFICIENCIA_PCT']:.2f}%\n\n"
            
            # Bloco de Votação
            if quer_votos:
                row_v = df_votos[df_votos['CD_MUNICIPIO'] == cid_cod]
                if not row_v.empty:
                    r_v = row_v.iloc[0]
                    resposta += "#### 🗳️ Resultados Eleitorais (1º Turno)\n"
                    resposta += f"*   **Presidente**:\n"
                    total_p = r_v['PRES_COMPARECIMENTO'] + r_v['PRES_ABSTENCOES']
                    abst_pct = (r_v['PRES_ABSTENCOES'] / total_p) * 100 if total_p > 0 else 0
                    resposta += f"    *   Comparecimento: {r_v['PRES_COMPARECIMENTO']:,.0f} | Abstenções: {r_v['PRES_ABSTENCOES']:,.0f} ({abst_pct:.2f}%)\n".replace(",", ".")
                    resposta += f"    *   Brancos: {r_v['PRES_VOTOS_BRANCOS']:,.0f} | Nulos: {r_v['PRES_VOTOS_NULOS']:,.0f}\n".replace(",", ".")
                    
                    pres_cols = [c for c in df_votos.columns if c.startswith('PRES_VOTOS_') and c not in ['PRES_VOTOS_BRANCOS', 'PRES_VOTOS_NULOS']]
                    pres_votes = {c.replace('PRES_VOTOS_', ''): r_v[c] for c in pres_cols if r_v[c] > 0}
                    for cand, votos in sorted(pres_votes.items(), key=lambda x: x[1], reverse=True)[:3]:
                        resposta += f"    *   **{cand}**: {votos:,.0f} votos ({(votos/r_v['PRES_COMPARECIMENTO'])*100:.2f}%)\n".replace(",", ".")
                        
                    resposta += f"\n*   **Governador**:\n"
                    total_g = r_v['GOV_COMPARECIMENTO'] + r_v['GOV_ABSTENCOES']
                    abst_g_pct = (r_v['GOV_ABSTENCOES'] / total_g) * 100 if total_g > 0 else 0
                    resposta += f"    *   Comparecimento: {r_v['GOV_COMPARECIMENTO']:,.0f} | Abstenções: {r_v['GOV_ABSTENCOES']:,.0f} ({abst_g_pct:.2f}%)\n".replace(",", ".")
                    resposta += f"    *   Brancos: {r_v['GOV_VOTOS_BRANCOS']:,.0f} | Nulos: {r_v['GOV_VOTOS_NULOS']:,.0f}\n".replace(",", ".")
                    
                    gov_cols = [c for c in df_votos.columns if c.startswith('GOV_VOTOS_') and c not in ['GOV_VOTOS_BRANCOS', 'GOV_VOTOS_NULOS']]
                    gov_votes = {c.replace('GOV_VOTOS_', ''): r_v[c] for c in gov_cols if r_v[c] > 0}
                    for cand, votos in sorted(gov_votes.items(), key=lambda x: x[1], reverse=True)[:3]:
                        resposta += f"    *   **{cand}**: {votos:,.0f} votos ({(votos/r_v['GOV_COMPARECIMENTO'])*100:.2f}%)\n".replace(",", ".")
                    resposta += "\n"

            # Bloco de Escolaridade por Candidato
            if quer_escolaridade:
                df_ep_cid = df_edu_pres[df_edu_pres['CD_MUNICIPIO'] == cid_cod]
                df_eg_cid = df_edu_gov[df_edu_gov['CD_MUNICIPIO'] == cid_cod]
                
                if not df_ep_cid.empty or not df_eg_cid.empty:
                    resposta += "#### 🎓 Grau de Escolaridade Estimado por Eleitor de cada Candidato\n"
                    resposta += "*(Esta relação indica a composição do eleitorado estimado de cada candidato nesta cidade)*\n\n"
                    
                    if not df_ep_cid.empty:
                        resposta += "*   **Presidente da República**:\n"
                        top_pres = df_ep_cid.groupby('NM_URNA_CANDIDATO')['TOTAL_ESTIMATED'].first().nlargest(3).index.tolist()
                        for cand in top_pres:
                            df_c = df_ep_cid[df_ep_cid['NM_URNA_CANDIDATO'] == cand].sort_values(by='PCT', ascending=False)
                            resposta += f"    *   **{cand}**:\n"
                            for _, r in df_c.head(3).iterrows():
                                resposta += f"        *   {r['DS_GRAU_ESCOLARIDADE']}: {r['PCT']:.2f}%\n"
                                
                    if not df_eg_cid.empty:
                        resposta += "\n*   **Governador do Estado**:\n"
                        top_gov = df_eg_cid.groupby('NM_URNA_CANDIDATO')['TOTAL_ESTIMATED'].first().nlargest(3).index.tolist()
                        for cand in top_gov:
                            df_c = df_eg_cid[df_eg_cid['NM_URNA_CANDIDATO'] == cand].sort_values(by='PCT', ascending=False)
                            resposta += f"    *   **{cand}**:\n"
                            for _, r in df_c.head(3).iterrows():
                                resposta += f"        *   {r['DS_GRAU_ESCOLARIDADE']}: {r['PCT']:.2f}%\n"
            
            return {
                "kind": "local_analyst_municipality",
                "answer": resposta
            }
            
        # 3. Caso não mencione cidade específica, verificar estatísticas estaduais ou gerais
        if any(w in lowered for w in ("paraíba", "estado", "pb", "geral", "escolaridade")):
            resposta = (
                "### 🏛️ Perfil Demográfico Geral - Estado da Paraíba (PB)\n\n"
                "A Paraíba conta com **3.091.684** eleitores aptos nas eleições de 2022:\n"
                "- **Gênero**: Feminino 52.86% (1.634.223) | Masculino 47.14% (1.457.461)\n"
                "- **Biometria Cadastrada**: 93.63% (2.894.645 eleitores)\n"
                "- **Eleitores com Deficiência**: 0.58% (17.939 eleitores)\n\n"
                "#### 🎓 Grau de Escolaridade Geral da População de Eleitores:\n"
                "1. Ensino Fundamental Incompleto: **24.14%**\n"
                "2. Ensino Médio Completo: **21.82%**\n"
                "3. Lê e Escreve: **14.25%**\n"
                "4. Ensino Médio Incompleto: **14.67%**\n"
                "5. Superior Completo: **8.41%**\n"
                "6. Analfabeto: **6.83%**\n"
                "7. Outros graus de instrução: **9.88%**\n\n"
                "💡 *Dica: Para pesquisar uma cidade específica e ver o gráfico detalhado por candidato, basta digitar o nome dela no chat (ex: 'Me mostre Sousa' ou 'Como foi o perfil eleitoral de Cajazeiras?').*"
            )
            return {
                "kind": "local_analyst_state",
                "answer": resposta
            }

        # 4. Caso padrão: ajuda
        return {
            "kind": "help",
            "answer": (
                "### 👋 Olá! Sou o Analista Eleitoral Inteligente Local da Paraíba!\n\n"
                "Fui adaptado para rodar **100% offline** na rede da UFCG, garantindo acesso completo aos dados sem precisar de internet ou da API da OpenAI!\n\n"
                "Você pode me perguntar sobre qualquer cidade paraibana para analisar a relação entre candidatos, abstenções e grau de instrução:\n\n"
                "*   *\"Como foi a votação e escolaridade dos candidatos em Sousa?\"*\n"
                "*   *\"Qual o perfil dos eleitores de João Pessoa?\"*\n"
                "*   *\"Me mostre o resumo eleitoral de Patos\"*\n\n"
                "👉 **Basta digitar o nome de uma cidade da Paraíba acima no chat para iniciar o relatório!**"
            )
        }

    def answer(self, question: str) -> dict:
        """
        Método principal que responde usando o agente inteligente GPT da OpenAI (Opção 3).
        Caso a chave da API não esteja configurada ou ocorra algum erro (por exemplo, bloqueios
        de rede da universidade UFCG), recorre automaticamente ao analista local robusto.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY não encontrada no ambiente. Utilizando analista local inteligente offline.")
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
            logger.error(f"Erro na comunicação com a API da OpenAI: {e}. Executando fallback local inteligente.")
            return self.fallback_answer(question)
