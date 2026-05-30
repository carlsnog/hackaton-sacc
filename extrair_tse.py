import requests
import pandas as pd
import io
import zipfile
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

id_pacote = "resultados-2022"
url_pacote = f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={id_pacote}"

print("1. Conectando à API de Recursos do TSE...")

try:
    resposta = requests.get(url_pacote, headers=headers)
    resposta.raise_for_status()
    recursos = resposta.json()['result']['resources']
    
    url_zip = None
    url_zip_detalhe = None
    
    for r in recursos:
        nome_recurso = r.get('name', '').lower()
        url_link = r.get('url', '').lower()
        if 'votação nominal por município e zona' in nome_recurso or 'votacao_nominal_municipio_zona' in url_link:
            url_zip = r['url']
        elif 'detalhe da apuração por município e zona' in nome_recurso or 'detalhe_votacao_munzona' in url_link:
            url_zip_detalhe = r['url']

    if url_zip and url_zip_detalhe:
        zip_local = "votacao_nominal_2022.zip"
        if os.path.exists(zip_local):
            print("2a. Carregando o arquivo compactado de Votação Nominal do cache local...")
            with open(zip_local, 'rb') as lf:
                conteudo_zip = lf.read()
        else:
            print("2a. Baixando o arquivo compactado de Votação Nominal...")
            print("Aguarde um instante...")
            conteudo_zip = requests.get(url_zip, headers=headers).content
            with open(zip_local, 'wb') as lf:
                lf.write(conteudo_zip)
            print("-> [Sucesso] Votação Nominal em cache local.")
            
        zip_local_detalhe = "detalhe_votacao_munzona_2022.zip"
        if os.path.exists(zip_local_detalhe):
            print("2b. Carregando o arquivo de Detalhe da Apuração do cache local...")
            with open(zip_local_detalhe, 'rb') as lf:
                conteudo_zip_detalhe = lf.read()
        else:
            print("2b. Baixando o arquivo compactado de Detalhe da Apuração...")
            print("Aguarde um instante...")
            conteudo_zip_detalhe = requests.get(url_zip_detalhe, headers=headers).content
            with open(zip_local_detalhe, 'wb') as lf:
                lf.write(conteudo_zip_detalhe)
            print("-> [Sucesso] Detalhe da Apuração em cache local.")

        print("\n3. Processando dados da Presidência para a Paraíba (PB)...")
        
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
            arq_br = [arq for arq in z.namelist() if 'BR.csv' in arq.upper() or '_BR' in arq.upper()][0]
            with z.open(arq_br) as f:
                colunas_nominais = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
                df_nom = pd.read_csv(f, sep=';', encoding='iso-8859-1', usecols=colunas_nominais)
                
                df_nom.columns = df_nom.columns.str.strip()
                df_nom['DS_CARGO'] = df_nom['DS_CARGO'].str.strip()
                df_nom['NM_URNA_CANDIDATO'] = df_nom['NM_URNA_CANDIDATO'].str.strip()
                df_nom['SG_UF'] = df_nom['SG_UF'].str.strip()
                
                df_pres_filtrado = df_nom[(df_nom['NR_TURNO'] == 1) & 
                                          (df_nom['DS_CARGO'].str.lower() == 'presidente') & 
                                          (df_nom['SG_UF'] == 'PB')]
                
                placar_pres_cands = df_pres_filtrado.groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index()
                placar_pres_cands.columns = ['NM_VOTAVEL', 'QT_VOTOS']

        with zipfile.ZipFile(io.BytesIO(conteudo_zip_detalhe)) as z_det:
            arq_det_br = [arq for arq in z_det.namelist() if 'BR.csv' in arq.upper() or '_BR' in arq.upper()][0]
            with z_det.open(arq_det_br) as f_det:
                colunas_detalhe = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
                df_det = pd.read_csv(f_det, sep=';', encoding='iso-8859-1', usecols=colunas_detalhe)
                
                df_det.columns = df_det.columns.str.strip()
                df_det['DS_CARGO'] = df_det['DS_CARGO'].str.strip()
                df_det['SG_UF'] = df_det['SG_UF'].str.strip()
                
                df_det_filtrado = df_det[(df_det['NR_TURNO'] == 1) & 
                                         (df_det['DS_CARGO'].str.lower() == 'presidente') & 
                                         (df_det['SG_UF'] == 'PB')]
                
                pres_aptos = df_det_filtrado['QT_APTOS'].sum()
                pres_comparecimento = df_det_filtrado['QT_COMPARECIMENTO'].sum()
                pres_abstencoes = df_det_filtrado['QT_ABSTENCOES'].sum()
                pres_brancos = df_det_filtrado['QT_VOTOS_BRANCOS'].sum()
                pres_nulos = df_det_filtrado['QT_TOTAL_VOTOS_NULOS'].sum()

        df_pres_brancos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': pres_brancos}])
        df_pres_nulos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': pres_nulos}])
        
        placar_pres = pd.concat([placar_pres_cands, df_pres_brancos, df_pres_nulos], ignore_index=True)
        placar_pres = placar_pres.sort_values(by='QT_VOTOS', ascending=False).reset_index(drop=True)
        
        print("\n========================================================")
        print("    PARTICIPAÇÃO E ABSTENÇÃO - PRESIDÊNCIA (PARAÍBA)")
        print("========================================================")
        print(f"Eleitores Aptos (PB): {pres_aptos:>15,.0f}".replace(",", "."))
        print(f"Total Comparecimento: {pres_comparecimento:>15,.0f} | {(pres_comparecimento/pres_aptos)*100:.2f}%".replace(",", "."))
        print(f"Total Abstenção (PB): {pres_abstencoes:>15,.0f} | {(pres_abstencoes/pres_aptos)*100:.2f}%".replace(",", "."))
        print("========================================================\n")
        
        print("========================================================")
        print("          PLACAR COMPLETO (PRESIDENTE - PARAÍBA)        ")
        print("========================================================")
        print(f"{'Candidato / Opção':<22} | {'Votos Absolutos':<15} | {'%'}")
        print("-" * 56)
        
        pres_validos = pres_comparecimento - pres_brancos - pres_nulos
        
        for _, linha in placar_pres.iterrows():
            nome = linha['NM_VOTAVEL']
            votos = linha['QT_VOTOS']
            
            if nome in ['VOTO BRANCO', 'VOTO NULO']:
                pct = (votos / pres_comparecimento) * 100
                tipo = "s/ Total"
            else:
                pct = (votos / pres_validos) * 100
                tipo = "s/ Válidos"
                
            print(f"{nome:<22} | {votos:>15,.0f} | {pct:.2f}% {tipo}".replace(",", "."))
        print("========================================================")

        df = placar_pres_cands
        ultima_linha = df_det_filtrado.sum()
        lista_dicionarios = df.to_dict(orient='records')
        lista_dicionarios.append({'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': int(ultima_linha['QT_VOTOS_BRANCOS'])})
        lista_dicionarios.append({'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': int(ultima_linha['QT_TOTAL_VOTOS_NULOS'])})
        lista_dicionarios = sorted(lista_dicionarios, key=lambda x: x['QT_VOTOS'], reverse=True)
        df_final = pd.DataFrame(lista_dicionarios)
        df_final.to_csv('resultado_presidente_pb_2022.csv', sep=';', index=False)

        print("\n4. Processando dados de Governador para a Paraíba (PB)...")
        
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
            arq_pb = [arq for arq in z.namelist() if 'PB.csv' in arq.upper() or '_PB' in arq.upper()][0]
            with z.open(arq_pb) as f:
                colunas_nominais = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
                df_gov = pd.read_csv(f, sep=';', encoding='iso-8859-1', usecols=colunas_nominais)
                
                df_gov.columns = df_gov.columns.str.strip()
                df_gov['DS_CARGO'] = df_gov['DS_CARGO'].str.strip()
                df_gov['NM_URNA_CANDIDATO'] = df_gov['NM_URNA_CANDIDATO'].str.strip()
                
                df_gov_filtrado = df_gov[(df_gov['NR_TURNO'] == 1) & (df_gov['DS_CARGO'].str.lower() == 'governador')]
                placar_gov_cands = df_gov_filtrado.groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index()
                placar_gov_cands.columns = ['NM_VOTAVEL', 'QT_VOTOS']

        with zipfile.ZipFile(io.BytesIO(conteudo_zip_detalhe)) as z_det:
            arq_pb_det = [arq for arq in z_det.namelist() if 'PB.csv' in arq.upper() or '_PB' in arq.upper()][0]
            with z_det.open(arq_pb_det) as f_det:
                colunas_detalhe = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
                df_det = pd.read_csv(f_det, sep=';', encoding='iso-8859-1', usecols=colunas_detalhe)
                
                df_det.columns = df_det.columns.str.strip()
                df_det['DS_CARGO'] = df_det['DS_CARGO'].str.strip()
                
                df_det_filtrado = df_det[(df_det['NR_TURNO'] == 1) & (df_det['DS_CARGO'].str.lower() == 'governador')]
                
                gov_aptos = df_det_filtrado['QT_APTOS'].sum()
                gov_comparecimento = df_det_filtrado['QT_COMPARECIMENTO'].sum()
                gov_abstencoes = df_det_filtrado['QT_ABSTENCOES'].sum()
                gov_brancos = df_det_filtrado['QT_VOTOS_BRANCOS'].sum()
                gov_nulos = df_det_filtrado['QT_TOTAL_VOTOS_NULOS'].sum()

        df_gov_brancos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': gov_brancos}])
        df_gov_nulos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': gov_nulos}])
        
        placar_gov = pd.concat([placar_gov_cands, df_gov_brancos, df_gov_nulos], ignore_index=True)
        placar_gov = placar_gov.sort_values(by='QT_VOTOS', ascending=False).reset_index(drop=True)
        
        print("\n========================================================")
        print("     PARTICIPAÇÃO E ABSTENÇÃO - GOVERNADOR (PARAÍBA)    ")
        print("==================================================")
        print(f"Eleitores Aptos (PB): {gov_aptos:>15,.0f}".replace(",", "."))
        print(f"Total Comparecimento: {gov_comparecimento:>15,.0f} | {(gov_comparecimento/gov_aptos)*100:.2f}%".replace(",", "."))
        print(f"Total Abstenção (PB): {gov_abstencoes:>15,.0f} | {(gov_abstencoes/gov_aptos)*100:.2f}%".replace(",", "."))
        print("========================================================\n")
        
        print("========================================================")
        print("          PLACAR COMPLETO (GOVERNADOR - PARAÍBA)        ")
        print("========================================================")
        print(f"{'Candidato / Opção':<22} | {'Votos Absolutos':<15} | {'%'}")
        print("-" * 56)
        
        gov_validos = gov_comparecimento - gov_brancos - gov_nulos
        
        for _, linha in placar_gov.iterrows():
            nome = linha['NM_VOTAVEL']
            votos = linha['QT_VOTOS']
            
            if nome in ['VOTO BRANCO', 'VOTO NULO']:
                pct = (votos / gov_comparecimento) * 100
                tipo = "s/ Total"
            else:
                pct = (votos / gov_validos) * 100
                tipo = "s/ Válidos"
                
            print(f"{nome:<22} | {votos:>15,.0f} | {pct:.2f}% {tipo}".replace(",", "."))
        print("========================================================")

    else:
        print("Não foi possível localizar os links de Votação Nominal ou Detalhe da Apuração na API.")

except Exception as e:
    print(f"\nOcorreu um erro no processamento geral: {e}")