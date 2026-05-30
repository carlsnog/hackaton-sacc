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

id_pacote_eleitorado = "eleitorado-2022"
url_pacote_eleitorado = f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={id_pacote_eleitorado}"

print("1. Conectando à API de Recursos do TSE...")

try:
    print(f"   -> Acessando API de Resultados: {url_pacote}")
    resposta = requests.get(url_pacote, headers=headers)
    resposta.raise_for_status()
    recursos = resposta.json()['result']['resources']
    
    print(f"   -> Acessando API de Eleitorado: {url_pacote_eleitorado}")
    resposta_el = requests.get(url_pacote_eleitorado, headers=headers)
    resposta_el.raise_for_status()
    recursos_el = resposta_el.json()['result']['resources']
    
    url_zip = None
    url_zip_detalhe = None
    url_zip_perfil = None
    
    for r in recursos:
        nome_recurso = r.get('name', '').lower()
        url_link = r.get('url', '').lower()
        if 'votação nominal por município e zona' in nome_recurso or 'votacao_nominal_municipio_zona' in url_link:
            url_zip = r['url']
        elif 'detalhe da apuração por município e zona' in nome_recurso or 'detalhe_votacao_munzona' in url_link:
            url_zip_detalhe = r['url']

    for r in recursos_el:
        nome_recurso = r.get('name', '').lower()
        url_link = r.get('url', '').lower()
        if 'eleitorado - 2022' in nome_recurso or 'perfil_eleitorado_2022' in url_link:
            url_zip_perfil = r['url']

    if url_zip and url_zip_detalhe and url_zip_perfil:
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

        zip_local_perfil = "perfil_eleitorado_2022.zip"
        if os.path.exists(zip_local_perfil):
            print("2c. Carregando o arquivo de Perfil do Eleitorado do cache local...")
            with open(zip_local_perfil, 'rb') as lf:
                conteudo_zip_perfil = lf.read()
        else:
            print("2c. Baixando o arquivo compactado de Perfil do Eleitorado...")
            print("Aguarde um instante...")
            conteudo_zip_perfil = requests.get(url_zip_perfil, headers=headers).content
            with open(zip_local_perfil, 'wb') as lf:
                lf.write(conteudo_zip_perfil)
            print("-> [Sucesso] Perfil do Eleitorado em cache local.")

        print("\n3. Processando dados da Presidência para a Paraíba (PB)...")
        
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
            arq_br = [arq for arq in z.namelist() if 'BR.csv' in arq.upper() or '_BR' in arq.upper()][0]
            with z.open(arq_br) as f:
                colunas_nominais = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
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
                colunas_detalhe = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NR_ZONA', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
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

        print("\n3.1. Processando dados do Perfil de Escolaridade dos Eleitores (PB)...")
        print("   -> Lendo perfil do eleitorado de 2022...")
        with zipfile.ZipFile(io.BytesIO(conteudo_zip_perfil)) as z_prof:
            chunks = []
            for chunk in pd.read_csv(z_prof.open('perfil_eleitorado_2022.csv'), sep=';', encoding='iso-8859-1', chunksize=100000):
                chunks.append(chunk[chunk['SG_UF'] == 'PB'])
            df_prof_pb = pd.concat(chunks, ignore_index=True)
        print(f"   -> [Sucesso] Carregado perfil do eleitorado (PB): {len(df_prof_pb)} registros.")

        # Agrupar perfil do eleitorado e calcular as frações de escolaridade por município e zona
        df_prof_grouped = df_prof_pb.groupby(['CD_MUNICIPIO', 'NR_ZONA', 'DS_GRAU_ESCOLARIDADE'])['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_prof_total = df_prof_pb.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_ELEITORES_PERFIL'].sum().reset_index(name='TOTAL_MUN_ZONA')
        df_prof_frac = pd.merge(df_prof_grouped, df_prof_total, on=['CD_MUNICIPIO', 'NR_ZONA'])
        df_prof_frac['FRACTION'] = df_prof_frac['QT_ELEITORES_PERFIL'] / df_prof_frac['TOTAL_MUN_ZONA']

        # Preparar dados de votos (candidatos + brancos + nulos) por município e zona
        df_pres_brancos = df_det_filtrado.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_VOTOS_BRANCOS'].sum().reset_index()
        df_pres_brancos.rename(columns={'QT_VOTOS_BRANCOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_pres_brancos['NM_URNA_CANDIDATO'] = 'VOTO BRANCO'

        df_pres_nulos = df_det_filtrado.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_TOTAL_VOTOS_NULOS'].sum().reset_index()
        df_pres_nulos.rename(columns={'QT_TOTAL_VOTOS_NULOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_pres_nulos['NM_URNA_CANDIDATO'] = 'VOTO NULO'

        df_votos_all_pres = pd.concat([
            df_pres_filtrado[['CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']],
            df_pres_brancos,
            df_pres_nulos
        ], ignore_index=True)

        # Cruzar os votos com o perfil de eleitores
        df_merged_pres = pd.merge(df_votos_all_pres, df_prof_frac, on=['CD_MUNICIPIO', 'NR_ZONA'])
        df_merged_pres['ESTIMATED_VOTES'] = df_merged_pres['QT_VOTOS_NOMINAIS'] * df_merged_pres['FRACTION']

        df_cand_edu_pres = df_merged_pres.groupby(['NM_URNA_CANDIDATO', 'DS_GRAU_ESCOLARIDADE'])['ESTIMATED_VOTES'].sum().reset_index()
        df_cand_total_pres = df_merged_pres.groupby(['NM_URNA_CANDIDATO'])['ESTIMATED_VOTES'].sum().reset_index(name='TOTAL_ESTIMATED')
        df_result_pres = pd.merge(df_cand_edu_pres, df_cand_total_pres, on=['NM_URNA_CANDIDATO'])
        df_result_pres['PCT'] = (df_result_pres['ESTIMATED_VOTES'] / df_result_pres['TOTAL_ESTIMATED']) * 100

        # Pivotar e ordenar os graus de escolaridade
        ordem_escolaridade = [
            'ANALFABETO',
            'LÊ E ESCREVE',
            'ENSINO FUNDAMENTAL INCOMPLETO',
            'ENSINO FUNDAMENTAL COMPLETO',
            'ENSINO MÉDIO INCOMPLETO',
            'ENSINO MÉDIO COMPLETO',
            'SUPERIOR INCOMPLETO',
            'SUPERIOR COMPLETO',
            'NÃO INFORMADO'
        ]

        df_pivot_pres = df_result_pres.pivot(index='DS_GRAU_ESCOLARIDADE', columns='NM_URNA_CANDIDATO', values='PCT')
        df_pivot_pres = df_pivot_pres.reindex(ordem_escolaridade)

        # Selecionar os 5 principais candidatos/opções do placar geral para exibição comparativa
        top_cands_pres = placar_pres.head(5)['NM_VOTAVEL'].tolist()
        present_cols_pres = [c for c in top_cands_pres if c in df_pivot_pres.columns]
        df_pivot_subset_pres = df_pivot_pres[present_cols_pres]

        print("\n========================================================")
        print("    PERFIL ESTIMADO DE ESCOLARIDADE DO ELEITOR (PRESIDENTE - PB)   ")
        print("========================================================")
        headers_str = f"{'Grau de Escolaridade':<30}"
        for col in present_cols_pres:
            short_col = col[:12]
            headers_str += f" | {short_col:>12}"
        print(headers_str)
        print("-" * len(headers_str))

        for idx, row in df_pivot_subset_pres.iterrows():
            row_str = f"{idx:<30}"
            for col in present_cols_pres:
                val = row[col]
                val_str = f"{val:.2f}%" if not pd.isna(val) else "0.00%"
                row_str += f" | {val_str:>12}"
            print(row_str.replace(",", "."))
        print("========================================================")
        print("Link da API do TSE (Eleitorado): https://dadosabertos.tse.jus.br/dataset/eleitorado-2022")
        print("========================================================\n")

        # Salvar o perfil de escolaridade para CSV
        df_pivot_pres.to_csv('resultado_presidente_escolaridade_pb_2022.csv', sep=';')
        print("-> [Sucesso] Perfil de escolaridade salvo em 'resultado_presidente_escolaridade_pb_2022.csv'")

        # Salvar o placar tradicional do presidente
        df = placar_pres_cands
        ultima_linha = df_det_filtrado.sum()
        lista_dicionarios = df.to_dict(orient='records')
        lista_dicionarios.append({'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': int(ultima_linha['QT_VOTOS_BRANCOS'])})
        lista_dicionarios.append({'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': int(ultima_linha['QT_TOTAL_VOTOS_NULOS'])})
        lista_dicionarios = sorted(lista_dicionarios, key=lambda x: x['QT_VOTOS'], reverse=True)
        df_final = pd.DataFrame(lista_dicionarios)
        df_final.to_csv('resultado_presidente_pb_2022.csv', sep=';', index=False)
        print("-> [Sucesso] Placar de votação salvo em 'resultado_presidente_pb_2022.csv'")

    else:
        print("Não foi possível localizar os links de Votação Nominal, Detalhe da Apuração ou Perfil do Eleitorado na API.")

except Exception as e:
    print(f"\nOcorreu um erro no processamento geral: {e}")
