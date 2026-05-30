import requests
import pandas as pd
import io
import zipfile

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

id_pacote = "resultados-2022"
url_pacote = f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={id_pacote}"

try:
    print("1. Conectando à API de Resultados de 2022 do TSE...")
    resposta = requests.get(url_pacote, headers=headers)
    resposta.raise_for_status()
    recursos = resposta.json()['result']['resources']
    
    url_presi = None
    url_gov = None
    
    # Identifica os dois ZIPs necessários no catálogo da API
    for r in recursos:
        url_link = r['url'].lower()
        if 'historico_totalizacao_presidente_br_1t_2022' in url_link:
            url_presi = r['url']
        elif 'historico_totalizacao_governador_uf_1t_2022' in url_link:
            url_gov = r['url']

    # --- PARTE 1: PRESIDENTE (NACIONAL) ---
    if url_presi:
        print("\n2. Processando dados da Presidência...")
        content_presi = requests.get(url_presi, headers=headers).content
        with zipfile.ZipFile(io.BytesIO(content_presi)) as z:
            df = pd.read_csv(z.open(z.namelist()[0]), sep=';', encoding='iso-8859-1')
            
            # Limpeza radical de caracteres invisíveis no cabeçalho
            df.columns = df.columns.str.replace(r'\s+', '', regex=True).str.strip()
            ultima_linha = df.iloc[-1]
            
            total_aptos = int(ultima_linha['QT_APTOS_TOTAL'])
            total_comp = int(ultima_linha['QT_VOTOS_TOTAL_ACUMULADO'])
            total_abst = total_aptos - total_comp
            
            print("\n========================================================")
            print("    PARTICIPAÇÃO E ABSTENÇÃO - PRESIDÊNCIA 1º TURNO 2022")
            print("========================================================")
            print(f"Eleitores Aptos:      {total_aptos:>15,.0f}".replace(",", "."))
            print(f"Total Comparecimento: {total_comp:>15,.0f} | {(total_comp/total_aptos)*100:.2f}%".replace(",", "."))
            print(f"Total Abstenção:      {total_abst:>15,.0f} | {(total_abst/total_aptos)*100:.2f}%".replace(",", "."))
            print("========================================================\n")
            
            # Mapeia os votos de forma dinâmica olhando o final da coluna
            votos_brancos = int(ultima_linha['BRANCO_QT_VOTOS_TOT_ACUMULADO'])
            votos_nulos = int(ultima_linha['NULO_QT_VOTOS_TOT_ACUMULADO'])
            votos_validos = total_comp - votos_brancos - votos_nulos
            
            print("========================================================")
            print("          PLACAR COMPLETO (PRESIDENTE - BRASIL)         ")
            print("========================================================")
            print(f"{'Candidato / Opção':<22} | {'Votos Absolutos':<15} | {'%'}")
            print("-" * 56)
            
            # Varre as colunas dinamicamente buscando os acumulados
            for col in df.columns:
                if col.endswith('_QT_VOTOS_TOT_ACUMULADO'):
                    nome_cand = col.replace('_QT_VOTOS_TOT_ACUMULADO', '').replace('_', ' ').title()
                    votos = int(ultima_linha[col])
                    
                    if votos > 0: # Ignora candidatos com zero votos se houver
                        porcentagem = (votos / votos_validos) * 100
                        print(f"{nome_cand:<22} | {votos:>15,.0f} | {porcentagem:.2f}% s/ Válidos".replace(",", "."))
            
            print(f"{'Votos Brancos':<22} | {votos_brancos:>15,.0f} | {(votos_brancos/total_comp)*100:.2f}% s/ Total".replace(",", "."))
            print(f"{'Votos Nulos':<22} | {votos_nulos:>15,.0f} | {(votos_nulos/total_comp)*100:.2f}% s/ Total".replace(",", "."))
            print("========================================================")

    # --- PARTE 2: GOVERNADOR (PARAÍBA) ---
    if url_gov:
        print("\n3. Processando dados de Governador para a Paraíba (PB)...")
        content_gov = requests.get(url_gov, headers=headers).content
        with zipfile.ZipFile(io.BytesIO(content_gov)) as z:
            
            # O arquivo de governadores vem dividido por UF dentro do zip. Vamos caçar o da PB:
            arq_pb = [arq for arq in z.namelist() if 'PB' in arq.upper()][0]
            
            df_gov = pd.read_csv(z.open(arq_pb), sep=';', encoding='iso-8859-1')
            df_gov.columns = df_gov.columns.str.replace(r'\s+', '', regex=True).str.strip()
            
            ultima_linha_gov = df_gov.iloc[-1]
            
            gov_aptos = int(ultima_linha_gov['QT_APTOS_TOTAL'])
            gov_comp = int(ultima_linha_gov['QT_VOTOS_TOTAL_ACUMULADO'])
            gov_abst = gov_aptos - gov_comp
            
            print("\n========================================================")
            print("     PARTICIPAÇÃO E ABSTENÇÃO - GOVERNADOR (PARAÍBA)    ")
            print("========================================================")
            print(f"Eleitores Aptos (PB): {gov_aptos:>15,.0f}".replace(",", "."))
            print(f"Total Comparecimento: {gov_comp:>15,.0f} | {(gov_comp/gov_aptos)*100:.2f}%".replace(",", "."))
            print(f"Total Abstenção (PB): {gov_abst:>15,.0f} | {(gov_abst/gov_aptos)*100:.2f}%".replace(",", "."))
            print("========================================================\n")
            
            gov_brancos = int(ultima_linha_gov['BRANCO_QT_VOTOS_TOT_ACUMULADO'])
            gov_nulos = int(ultima_linha_gov['NULO_QT_VOTOS_TOT_ACUMULADO'])
            gov_validos = gov_comp - gov_brancos - gov_nulos
            
            print("========================================================")
            print("          PLACAR COMPLETO (GOVERNADOR - PARAÍBA)        ")
            print("========================================================")
            print(f"{'Candidato / Opção':<22} | {'Votos Absolutos':<15} | {'%'}")
            print("-" * 56)
            
            for col in df_gov.columns:
                if col.endswith('_QT_VOTOS_TOT_ACUMULADO'):
                    nome_cand = col.replace('_QT_VOTOS_TOT_ACUMULADO', '').replace('_', ' ').title()
                    votos = int(ultima_linha_gov[col])
                    
                    if votos > 0:
                        porcentagem = (votos / gov_validos) * 100
                        print(f"{nome_cand:<22} | {votos:>15,.0f} | {porcentagem:.2f}% s/ Válidos".replace(",", "."))
                        
            print(f"{'Votos Brancos':<22} | {gov_brancos:>15,.0f} | {(gov_brancos/gov_comp)*100:.2f}% s/ Total".replace(",", "."))
            print(f"{'Votos Nulos':<22} | {gov_nulos:>15,.0f} | {(gov_nulos/gov_comp)*100:.2f}% s/ Total".replace(",", "."))
            print("========================================================")

except Exception as e:
    print(f"\nOcorreu um erro no processamento geral: {e}")