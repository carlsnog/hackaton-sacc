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

print("1. Acessando a API de Recursos do TSE...")

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
            print("Aguarde um instante (comunicando com o servidor do TSE)...")
            conteudo_zip = requests.get(url_zip, headers=headers).content
            with open(zip_local, 'wb') as lf:
                lf.write(conteudo_zip)
            print("-> [Sucesso] Arquivo de Votação Nominal salvo em cache local.")
            
        zip_local_detalhe = "detalhe_votacao_munzona_2022.zip"
        if os.path.exists(zip_local_detalhe):
            print("2b. Carregando o arquivo de Detalhe da Apuração do cache local...")
            with open(zip_local_detalhe, 'rb') as lf:
                conteudo_zip_detalhe = lf.read()
        else:
            print("2b. Baixando o arquivo compactado de Detalhe da Apuração...")
            print("Aguarde um instante (comunicando com o servidor do TSE)...")
            conteudo_zip_detalhe = requests.get(url_zip_detalhe, headers=headers).content
            with open(zip_local_detalhe, 'wb') as lf:
                lf.write(conteudo_zip_detalhe)
            print("-> [Sucesso] Arquivo de Detalhe da Apuração salvo em cache local.")

        zip_local_perfil = "perfil_eleitorado_2022.zip"
        if os.path.exists(zip_local_perfil):
            print("2c. Carregando o arquivo de Perfil do Eleitorado do cache local...")
            with open(zip_local_perfil, 'rb') as lf:
                conteudo_zip_perfil = lf.read()
        else:
            print("2c. Baixando o arquivo compactado de Perfil do Eleitorado...")
            print("Aguarde um instante (comunicando com o servidor do TSE)...")
            conteudo_zip_perfil = requests.get(url_zip_perfil, headers=headers).content
            with open(zip_local_perfil, 'wb') as lf:
                lf.write(conteudo_zip_perfil)
            print("-> [Sucesso] Arquivo de Perfil do Eleitorado salvo em cache local.")

        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
            arquivos_internos = z.namelist()
            arq_pb = [arq for arq in arquivos_internos if 'PB.csv' in arq.upper() or '_PB' in arq.upper()]
            
            if arq_pb:
                arq_pb = arq_pb[0]
                print(f"3. Filtrando e processando o arquivo da Paraíba (Votos Nominais): {arq_pb}")
                
                with z.open(arq_pb) as f:
                    colunas_nominais = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
                    df = pd.read_csv(f, sep=';', encoding='iso-8859-1', usecols=colunas_nominais)
                    
                    df.columns = df.columns.str.strip()
                    df['DS_CARGO'] = df['DS_CARGO'].str.strip()
                    df['NM_URNA_CANDIDATO'] = df['NM_URNA_CANDIDATO'].str.strip()
                    
                    df_filtrado = df[(df['NR_TURNO'] == 1) & (df['DS_CARGO'].str.lower() == 'governador')]
                    placar_cands = df_filtrado.groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index()
                    placar_cands.columns = ['NM_VOTAVEL', 'QT_VOTOS']
            else:
                raise FileNotFoundError("Não encontramos o arquivo da PB dentro do ZIP de Votação Nominal.")

        with zipfile.ZipFile(io.BytesIO(conteudo_zip_detalhe)) as z_det:
            arquivos_internos_det = z_det.namelist()
            arq_pb_det = [arq for arq in arquivos_internos_det if 'PB.csv' in arq.upper() or '_PB' in arq.upper()]
            
            if arq_pb_det:
                arq_pb_det = arq_pb_det[0]
                print(f"4. Filtrando e processando o arquivo da Paraíba (Detalhe da Apuração): {arq_pb_det}")
                
                with z_det.open(arq_pb_det) as f_det:
                    colunas_detalhe = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NR_ZONA', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
                    df_det = pd.read_csv(f_det, sep=';', encoding='iso-8859-1', usecols=colunas_detalhe)
                    
                    df_det.columns = df_det.columns.str.strip()
                    df_det['DS_CARGO'] = df_det['DS_CARGO'].str.strip()
                    
                    df_det_filtrado = df_det[(df_det['NR_TURNO'] == 1) & (df_det['DS_CARGO'].str.lower() == 'governador')]
                    
                    votos_aptos = df_det_filtrado['QT_APTOS'].sum()
                    votos_comparecimento = df_det_filtrado['QT_COMPARECIMENTO'].sum()
                    votos_abstencoes = df_det_filtrado['QT_ABSTENCOES'].sum()
                    votos_brancos = df_det_filtrado['QT_VOTOS_BRANCOS'].sum()
                    votos_nulos = df_det_filtrado['QT_TOTAL_VOTOS_NULOS'].sum()
            else:
                raise FileNotFoundError("Não encontramos o arquivo da PB dentro do ZIP de Detalhe da Apuração.")

        df_brancos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': votos_brancos}])
        df_nulos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': votos_nulos}])
        
        placar = pd.concat([placar_cands, df_brancos, df_nulos], ignore_index=True)
        placar = placar.sort_values(by='QT_VOTOS', ascending=False).reset_index(drop=True)
        
        print("\n========================================================")
        print("     PARTICIPAÇÃO E ABSTENÇÃO - GOVERNADOR (PARAÍBA)    ")
        print("========================================================")
        print(f"Eleitores Aptos (PB): {votos_aptos:>15,.0f}".replace(",", "."))
        print(f"Total Comparecimento: {votos_comparecimento:>15,.0f} | {(votos_comparecimento/votos_aptos)*100:.2f}%".replace(",", "."))
        print(f"Total Abstenção (PB): {votos_abstencoes:>15,.0f} | {(votos_abstencoes/votos_aptos)*100:.2f}%".replace(",", "."))
        print("========================================================\n")
        
        print("========================================================")
        print("          RESULTADO OFICIAL - GOVERNADOR PB 2022        ")
        print("========================================================\n")
        
        total_votos_apurados = placar['QT_VOTOS'].sum()
        votos_validos = total_votos_apurados - votos_brancos - votos_nulos
        
        print(f"Total de Votos Apurados na PB: {total_votos_apurados:>12,.0f}".replace(",", "."))
        print(f"Votos Válidos (Candidatos):    {votos_validos:>12,.0f}".replace(",", "."))
        print("-" * 56)
        print(f"{'Candidato / Opção':<25} | {'Votos Absolutos':<15} | {'%'}")
        print("-" * 56)
        
        for _, linha in placar.iterrows():
            nome = linha['NM_VOTAVEL']
            votos = linha['QT_VOTOS']
            
            if nome in ['VOTO BRANCO', 'VOTO NULO']:
                pct = (votos / total_votos_apurados) * 100
                tipo = "s/ Total"
            else:
                pct = (votos / votos_validos) * 100
                tipo = "s/ Válidos"
                
            print(f"{nome:<25} | {votos:>15,.0f} | {pct:.2f}% {tipo}".replace(",", "."))
        
        print("========================================================")
        
        # Preparar dados de escolaridade para Governador
        print("\n4.1. Processando dados do Perfil de Escolaridade dos Eleitores (PB)...")
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

        # Preparar dados de votos de Governador (candidatos + brancos + nulos) por município e zona
        df_gov_brancos = df_det_filtrado.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_VOTOS_BRANCOS'].sum().reset_index()
        df_gov_brancos.rename(columns={'QT_VOTOS_BRANCOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_gov_brancos['NM_URNA_CANDIDATO'] = 'VOTO BRANCO'

        df_gov_nulos = df_det_filtrado.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_TOTAL_VOTOS_NULOS'].sum().reset_index()
        df_gov_nulos.rename(columns={'QT_TOTAL_VOTOS_NULOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_gov_nulos['NM_URNA_CANDIDATO'] = 'VOTO NULO'

        df_votos_all_gov = pd.concat([
            df_filtrado[['CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']],
            df_gov_brancos,
            df_gov_nulos
        ], ignore_index=True)

        # Cruzar os votos com o perfil de eleitores
        df_merged_gov = pd.merge(df_votos_all_gov, df_prof_frac, on=['CD_MUNICIPIO', 'NR_ZONA'])
        df_merged_gov['ESTIMATED_VOTES'] = df_merged_gov['QT_VOTOS_NOMINAIS'] * df_merged_gov['FRACTION']

        df_cand_edu_gov = df_merged_gov.groupby(['NM_URNA_CANDIDATO', 'DS_GRAU_ESCOLARIDADE'])['ESTIMATED_VOTES'].sum().reset_index()
        df_cand_total_gov = df_merged_gov.groupby(['NM_URNA_CANDIDATO'])['ESTIMATED_VOTES'].sum().reset_index(name='TOTAL_ESTIMATED')
        df_result_gov = pd.merge(df_cand_edu_gov, df_cand_total_gov, on=['NM_URNA_CANDIDATO'])
        df_result_gov['PCT'] = (df_result_gov['ESTIMATED_VOTES'] / df_result_gov['TOTAL_ESTIMATED']) * 100

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

        df_pivot_gov = df_result_gov.pivot(index='DS_GRAU_ESCOLARIDADE', columns='NM_URNA_CANDIDATO', values='PCT')
        df_pivot_gov = df_pivot_gov.reindex(ordem_escolaridade)

        # Selecionar os 5 principais candidatos/opções do placar geral de Governador para exibição
        top_cands_gov = placar.head(5)['NM_VOTAVEL'].tolist()
        present_cols_gov = [c for c in top_cands_gov if c in df_pivot_gov.columns]
        df_pivot_subset_gov = df_pivot_gov[present_cols_gov]

        print("\n========================================================")
        print("    PERFIL ESTIMADO DE ESCOLARIDADE DO ELEITOR (GOVERNADOR - PB)   ")
        print("========================================================")
        headers_str = f"{'Grau de Escolaridade':<30}"
        for col in present_cols_gov:
            short_col = col[:12]
            headers_str += f" | {short_col:>12}"
        print(headers_str)
        print("-" * len(headers_str))

        for idx, row in df_pivot_subset_gov.iterrows():
            row_str = f"{idx:<30}"
            for col in present_cols_gov:
                val = row[col]
                val_str = f"{val:.2f}%" if not pd.isna(val) else "0.00%"
                row_str += f" | {val_str:>12}"
            print(row_str.replace(",", "."))
        print("========================================================")
        print("Link da API do TSE (Eleitorado): https://dadosabertos.tse.jus.br/dataset/eleitorado-2022")
        print("========================================================\n")

        # Salvar o perfil de escolaridade para CSV
        df_pivot_gov.to_csv('resultado_governador_escolaridade_pb_2022.csv', sep=';')
        print("-> [Sucesso] Perfil de escolaridade salvo em 'resultado_governador_escolaridade_pb_2022.csv'")

        placar.to_csv("resultado_governador_pb_2022.csv", index=False, sep=";")
        print("-> [Sucesso] Placar de votação salvo em 'resultado_governador_pb_2022.csv'")
        
    else:
        print("Não foi possível localizar os links de Votação Nominal ou Detalhe da Apuração na API.")

except Exception as e:
    print(f"\nErro no processamento: {e}")