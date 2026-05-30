import os
import sys
import pandas as pd

# Arquivos de dados necessários
dem_file = 'perfil_demografico_municipios_pb_2022.csv'
votos_file = 'resultado_consolidado_municipios_pb_2022.csv'

# Verificação inicial dos dados
if not os.path.exists(dem_file) or not os.path.exists(votos_file):
    print("❌ Erro: Os arquivos consolidados de dados não foram encontrados.")
    print("Por favor, execute o script 'geral_eleitores_pb.py' primeiro para gerar os dados.")
    sys.exit(1)

# Carregar dados na memória
df_dem = pd.read_csv(dem_file, sep=';')
df_votos = pd.read_csv(votos_file, sep=';')

def obter_dados_cidade(nome_cidade: str) -> str:
    """
    Função que busca e formata os dados demográficos e de apuração de votos
    para uma cidade específica da Paraíba.
    """
    nome_cidade = nome_cidade.strip().upper()
    
    # 1. Buscar demografia
    cidades_dem = df_dem[df_dem['NM_MUNICIPIO'].str.upper() == nome_cidade]
    if cidades_dem.empty:
        # Sugerir nomes semelhantes se não encontrar
        sugestoes = df_dem[df_dem['NM_MUNICIPIO'].str.upper().str.contains(nome_cidade, na=False)]['NM_MUNICIPIO'].tolist()
        sugest_str = f" Você quis dizer: {', '.join(sugestoes[:3])}?" if sugestoes else ""
        return f"Erro: A cidade '{nome_cidade}' não foi encontrada no banco demográfico da PB.{sugest_str}"
        
    row_dem = cidades_dem.iloc[0]
    
    # Formatar Bloco Demográfico
    dem_info = (
        f"--- DADOS DEMOGRÁFICOS DE {row_dem['NM_MUNICIPIO']} (PB) ---\n"
        f"- Total de Eleitores Aptos: {row_dem['TOTAL_ELEITORES']:,.0f}\n"
        f"- Biometria Cadastrada: {row_dem['BIOMETRIA_PCT']:.2f}%\n"
        f"- Eleitores com Deficiência: {row_dem['DEFICIENCIA_PCT']:.2f}%\n"
        f"- Gênero Feminino: {row_dem['GENERO_FEMININO_PCT']:.2f}%\n"
        f"- Gênero Masculino: {row_dem['GENERO_MASCULINO_PCT']:.2f}%\n"
        f"- Escolaridade:\n"
    )
    
    # Adicionar porcentagens de escolaridade maiores que 0%
    edu_cols = [c for c in df_dem.columns if c.startswith('ESCOLARIDADE_')]
    edu_vals = {c.replace('ESCOLARIDADE_', '').replace('_PCT', ''): row_dem[c] for c in edu_cols}
    for edu_cat, edu_val in sorted(edu_vals.items(), key=lambda x: x[1], reverse=True):
        if edu_val > 0:
            dem_info += f"  * {edu_cat}: {edu_val:.2f}%\n"
            
    # 2. Buscar votos
    row_v = df_votos[df_votos['CD_MUNICIPIO'] == row_dem['CD_MUNICIPIO']]
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
            
    return dem_info + votes_info

# Tenta importar as bibliotecas da OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("\n❌ Erro: O pacote 'openai' não está instalado.")
    print("Para utilizar este assistente inteligente de IA, instale o pacote oficial rodando:")
    print("👉 pip install openai\n")
    sys.exit(1)

# Inicializar o cliente OpenAI
# Carrega automaticamente a chave de ambiente OPENAI_API_KEY
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    print("\n⚠️ Atenção: A variável de ambiente 'OPENAI_API_KEY' não foi encontrada.")
    print("Por favor, configure sua chave de API antes de executar este script:")
    print("No Linux/macOS: export OPENAI_API_KEY='sua-chave-aqui'")
    print("No Windows: set OPENAI_API_KEY='sua-chave-aqui'\n")
    sys.exit(1)

client = OpenAI(api_key=api_key)

print("\n" + "="*56)
print("     ASSISTENTE DE IA DO ELEITORADO DA PARAÍBA (PB)     ")
print("="*56)
print("Olá! Eu sou o seu assistente de IA. Você pode me fazer perguntas")
print("sobre a demografia e resultados de votação de qualquer cidade")
print("da Paraíba. Eu buscarei as informações reais e farei análises")
print("relevantes e inteligentes para você.")
print("Digite 'sair' ou Enter vazio a qualquer momento para encerrar.\n")

# Prompt do Sistema para instruir o comportamento do modelo
system_prompt = (
    "Você é um cientista político especialista nas eleições e eleitorado do estado da Paraíba (PB). "
    "Seu papel é responder perguntas dos usuários de forma inteligente e analítica. "
    "Você tem acesso à ferramenta 'obter_dados_cidade' para obter dados reais de qualquer cidade. "
    "Sempre que o usuário citar uma cidade ou perguntar sobre ela, use a ferramenta para buscar os dados."
    "Após receber os dados, faça uma análise crítica: identifique quem venceu, analise as taxas de abstenção "
    "e relacione o resultado eleitoral com o perfil demográfico (como gênero e escolaridade) daquela cidade."
)

import json

while True:
    pergunta = input("\n👤 Sua pergunta: ").strip()
    if not pergunta or pergunta.lower() == 'sair':
        print("Até mais!")
        break
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pergunta}
    ]
    
    print("🤖 Pensando e analisando dados...")
    
    # 1. Chamar o modelo com suporte a Tool/Function Calling
    tools = [{
        "type": "function",
        "function": {
            "name": "obter_dados_cidade",
            "description": "Retorna o perfil demográfico e os votos de Presidente e Governador de uma cidade da Paraíba.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_cidade": {
                        "type": "string",
                        "description": "Nome da cidade (ex: JOÃO PESSOA, SOUSA, CAMPINA GRANDE)."
                    }
                },
                "required": ["nome_cidade"]
            }
        }
    }]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo padrão econômico e rápido
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        
        # 2. Verificar se o modelo decidiu chamar nossa função
        if tool_calls:
            # Adiciona a resposta do modelo à conversa
            messages.append(response_message)
            
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                cidade = function_args.get("nome_cidade")
                
                print(f"🔍 [IA chamou a ferramenta] Buscando dados de: {cidade}...")
                
                # Executa a nossa função real
                resultado_busca = obter_dados_cidade(cidade)
                
                # Adiciona o resultado da ferramenta na conversa
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": resultado_busca
                })
            
            # 3. Segunda chamada para que o modelo processe os dados reais obtidos
            second_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )
            print("\n🤖 Resposta da IA:")
            print(second_response.choices[0].message.content)
            
        else:
            print("\n🤖 Resposta da IA:")
            print(response_message.content)
            
    except Exception as e:
        print(f"\n❌ Ocorreu um erro na comunicação com a API do OpenAI: {e}")
        print("Certifique-se de que sua OPENAI_API_KEY é válida e que possui créditos ativos.")
