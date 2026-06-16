import os
import sys
import json
from pipeline.core import load_env
from ai.assistant import obter_dados_cidade_completo

# Carregar as variáveis de ambiente a partir do .env
load_env()

# Identificar a chave de API e configurações de LLM
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY")
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/" if os.environ.get("GEMINI_API_KEY") else os.environ.get("LLM_BASE_URL")
model = os.environ.get("GEMINI_MODEL") or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL")

if not api_key:
    print("\nErro: Nenhuma chave de API (GEMINI_API_KEY ou OPENAI_API_KEY) foi encontrada.")
    print("Por favor, configure sua chave de API antes de executar este script no arquivo .env.")
    sys.exit(1)

if not model:
    model = "gemini-2.5-flash" if "googleapis.com" in (base_url or "") else "gpt-4o-mini"

# Tenta importar as bibliotecas da OpenAI
try:
    from openai import OpenAI
except ImportError:
    print("\nErro: O pacote 'openai' não está instalado.")
    print("Para utilizar este assistente inteligente de IA, instale o pacote oficial rodando:")
    print("pip install openai\n")
    sys.exit(1)

client = OpenAI(api_key=api_key, base_url=base_url)

print("\n" + "="*56)
print("     ANALISTA ELEITORAL DA PARAÍBA (PB)     ")
print("="*56)
print("Olá. Você pode fazer consultas sobre a demografia e resultados")
print("de votação de qualquer município da Paraíba. As informações")
print("são buscadas e analisadas diretamente de bases oficiais.")
print(f"Modelo ativo: {model} (Conexão: {'Gemini API' if 'googleapis.com' in (base_url or '') else 'OpenAI'})")
print("Digite 'sair' ou Enter vazio a qualquer momento para sair.\n")

# Prompt do Sistema para instruir o comportamento do modelo
system_prompt = (
    "Você é um cientista político especialista nas eleições e eleitorado do estado da Paraíba (PB).\n"
    "Seu papel é responder perguntas dos usuários de forma inteligente e analítica.\n"
    "Você tem acesso à ferramenta 'obter_dados_cidade' para obter dados reais de qualquer cidade.\n"
    "Sempre que o usuário citar uma cidade ou perguntar sobre ela, use a ferramenta para buscar os dados.\n"
    "Após receber os dados, faça uma análise crítica: apresente os dados demográficos de gênero e escolaridade, "
    "os dados eleitorais de comparecimento, abstenção e votos válidos, e explique que estatísticas individuais de candidatos "
    "não estão carregadas no datamart atual do projeto.\n\n"
    "REGRAS CRÍTICAS E OBRIGATÓRIAS:\n"
    "1. NUNCA utilize nenhum tipo de emoji ou símbolos decorativos semelhantes em suas respostas.\n"
    "2. NUNCA declare ser uma inteligência artificial, LLM, assistente virtual, chatbot ou algo semelhante. Fale sempre e diretamente como um cientista político humano de forma profissional."
)

while True:
    pergunta = input("\nSua pergunta: ").strip()
    if not pergunta or pergunta.lower() == 'sair':
        print("Até mais!")
        break
        
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": pergunta}
    ]
    
    print("Pensando e analisando dados...")
    
    # 1. Chamar o modelo com suporte a Tool/Function Calling
    tools = [{
        "type": "function",
        "function": {
            "name": "obter_dados_cidade",
            "description": "Retorna o perfil demográfico, estatísticas de votação e renda de uma cidade da Paraíba.",
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
            model=model,
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
                
                print(f"[Buscando dados de: {cidade}...]")
                
                # Executa a nossa função real
                resultado_busca = obter_dados_cidade_completo(cidade)
                
                # Adiciona o resultado da ferramenta na conversa
                messages.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": resultado_busca
                })
            
            # 3. Segunda chamada para que o modelo processe os dados reais obtidos
            second_response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            print("\nResposta:")
            print(second_response.choices[0].message.content)
            
        else:
            print("\nResposta:")
            print(response_message.content)
            
    except Exception as e:
        print(f"\nOcorreu um erro na comunicação com a API: {e}")
