import requests
import pandas as pd
import io
import zipfile
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

id_pacote_eleitorado = "eleitorado-2022"
url_pacote_eleitorado = f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={id_pacote_eleitorado}"

print("1. Acessando a API do Perfil de Eleitorado do TSE...")

try:
    print(f"   -> Conectando a {url_pacote_eleitorado}...")
    resposta_el = requests.get(url_pacote_eleitorado, headers=headers)
    resposta_el.raise_for_status()
    recursos_el = resposta_el.json()['result']['resources']
    
    url_zip_perfil = None
    for r in recursos_el:
        nome_recurso = r.get('name', '').lower()
        url_link = r.get('url', '').lower()
        if 'eleitorado - 2022' in nome_recurso or 'perfil_eleitorado_2022' in url_link:
            url_zip_perfil = r['url']

    if url_zip_perfil:
        zip_local_perfil = "perfil_eleitorado_2022.zip"
        if os.path.exists(zip_local_perfil):
            print("2. Carregando o arquivo compactado de Perfil do Eleitorado do cache local...")
            with open(zip_local_perfil, 'rb') as lf:
                conteudo_zip_perfil = lf.read()
        else:
            print("2. Baixando o arquivo compactado de Perfil do Eleitorado (pode demorar alguns instantes)...")
            conteudo_zip_perfil = requests.get(url_zip_perfil, headers=headers).content
            with open(zip_local_perfil, 'wb') as lf:
                lf.write(conteudo_zip_perfil)
            print("-> [Sucesso] Perfil do Eleitorado em cache local.")

        print("\n3. Processando e consolidando informações do Eleitorado da Paraíba (PB)...")
        with zipfile.ZipFile(io.BytesIO(conteudo_zip_perfil)) as z_prof:
            chunks = []
            for chunk in pd.read_csv(z_prof.open('perfil_eleitorado_2022.csv'), sep=';', encoding='iso-8859-1', chunksize=100000):
                chunks.append(chunk[chunk['SG_UF'] == 'PB'])
            df_prof_pb = pd.concat(chunks, ignore_index=True)

        # Agrupar perfil do eleitorado e calcular as frações de escolaridade por município e zona
        df_prof_grouped = df_prof_pb.groupby(['CD_MUNICIPIO', 'NR_ZONA', 'DS_GRAU_ESCOLARIDADE'])['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_prof_total = df_prof_pb.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_ELEITORES_PERFIL'].sum().reset_index(name='TOTAL_MUN_ZONA')
        df_prof_frac = pd.merge(df_prof_grouped, df_prof_total, on=['CD_MUNICIPIO', 'NR_ZONA'])
        df_prof_frac['FRACTION'] = df_prof_frac['QT_ELEITORES_PERFIL'] / df_prof_frac['TOTAL_MUN_ZONA']


        # 3.1. Processar demografia por município (PB)
        print("   -> Calculando perfil demográfico de cada município paraibano...")
        
        # Totais, biometria e deficiência por município
        df_tot_mun = df_prof_pb.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO'])[['QT_ELEITORES_PERFIL', 'QT_ELEITORES_BIOMETRIA', 'QT_ELEITORES_DEFICIENCIA']].sum().reset_index()
        df_tot_mun.rename(columns={
            'QT_ELEITORES_PERFIL': 'TOTAL_ELEITORES',
            'QT_ELEITORES_BIOMETRIA': 'BIOMETRIA_ABS',
            'QT_ELEITORES_DEFICIENCIA': 'DEFICIENCIA_ABS'
        }, inplace=True)
        df_tot_mun['BIOMETRIA_PCT'] = (df_tot_mun['BIOMETRIA_ABS'] / df_tot_mun['TOTAL_ELEITORES']) * 100
        df_tot_mun['DEFICIENCIA_PCT'] = (df_tot_mun['DEFICIENCIA_ABS'] / df_tot_mun['TOTAL_ELEITORES']) * 100

        # Gênero por município
        df_gender_mun = df_prof_pb.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO', 'DS_GENERO'])['QT_ELEITORES_PERFIL'].sum().unstack(fill_value=0)
        df_gender_mun_pct = df_gender_mun.div(df_gender_mun.sum(axis=1), axis=0) * 100
        df_gender_mun_pct.columns = ['GENERO_' + str(c) + '_PCT' for c in df_gender_mun_pct.columns]
        df_gender_mun_pct = df_gender_mun_pct.reset_index()

        # Escolaridade por município
        df_edu_mun = df_prof_pb.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO', 'DS_GRAU_ESCOLARIDADE'])['QT_ELEITORES_PERFIL'].sum().unstack(fill_value=0)
        df_edu_mun_pct = df_edu_mun.div(df_edu_mun.sum(axis=1), axis=0) * 100
        df_edu_mun_pct.columns = ['ESCOLARIDADE_' + str(c) + '_PCT' for c in df_edu_mun_pct.columns]
        df_edu_mun_pct = df_edu_mun_pct.reset_index()

        # Estado civil por município
        df_civil_mun = df_prof_pb.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO', 'DS_ESTADO_CIVIL'])['QT_ELEITORES_PERFIL'].sum().unstack(fill_value=0)
        df_civil_mun_pct = df_civil_mun.div(df_civil_mun.sum(axis=1), axis=0) * 100
        df_civil_mun_pct.columns = ['ESTADO_CIVIL_' + str(c) + '_PCT' for c in df_civil_mun_pct.columns]
        df_civil_mun_pct = df_civil_mun_pct.reset_index()

        # Faixa etária por município
        df_age_mun = df_prof_pb.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO', 'DS_FAIXA_ETARIA'])['QT_ELEITORES_PERFIL'].sum().unstack(fill_value=0)
        df_age_mun_pct = df_age_mun.div(df_age_mun.sum(axis=1), axis=0) * 100
        df_age_mun_pct.columns = ['FAIXA_ETARIA_' + str(c) + '_PCT' for c in df_age_mun_pct.columns]
        df_age_mun_pct = df_age_mun_pct.reset_index()

        # Mesclar toda a demografia por município
        df_dem_mun = pd.merge(df_tot_mun, df_gender_mun_pct, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'])
        df_dem_mun = pd.merge(df_dem_mun, df_edu_mun_pct, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'])
        df_dem_mun = pd.merge(df_dem_mun, df_civil_mun_pct, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'])
        df_dem_mun = pd.merge(df_dem_mun, df_age_mun_pct, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'])

        # Salvar o banco de dados demográfico consolidado
        dem_cidades_file = 'perfil_demografico_municipios_pb_2022.csv'
        df_dem_mun.to_csv(dem_cidades_file, sep=';', index=False)
        print(f"   -> [Sucesso] Perfil demográfico de todos os {len(df_dem_mun)} municípios salvo em '{dem_cidades_file}'")

        # Exibir amostra de perfil demográfico para as principais cidades
        amostra_cidades = ['JOÃO PESSOA', 'CAMPINA GRANDE', 'PATOS']
        df_amostra = df_dem_mun[df_dem_mun['NM_MUNICIPIO'].isin(amostra_cidades)]
        
        print("\n========================================================")
        print("  PAINEL DEMOGRÁFICO DE ELEITORES POR MUNICÍPIO (PB)    ")
        print("========================================================")
        for _, row in df_amostra.iterrows():
            print(f"Município: {row['NM_MUNICIPIO']}")
            print(f"  - Total de Eleitores Aptos: {row['TOTAL_ELEITORES']:,.0f}".replace(",", "."))
            print(f"  - Biometria Cadastrada:     {row['BIOMETRIA_PCT']:.2f}%")
            print(f"  - Gênero Feminino:          {row['GENERO_FEMININO_PCT']:.2f}%")
            print(f"  - Gênero Masculino:         {row['GENERO_MASCULINO_PCT']:.2f}%")
            print(f"  - Escolaridade (Top 3):")
            city_edu_cols = [c for c in df_dem_mun.columns if c.startswith('ESCOLARIDADE_')]
            city_edu_vals = {c.replace('ESCOLARIDADE_', '').replace('_PCT', ''): row[c] for c in city_edu_cols}
            sorted_edu = sorted(city_edu_vals.items(), key=lambda x: x[1], reverse=True)[:3]
            for edu_cat, edu_val in sorted_edu:
                print(f"    * {edu_cat:<30}: {edu_val:.2f}%")
            print("-" * 56)
        print("========================================================\n")

        total_eleitores = df_prof_pb['QT_ELEITORES_PERFIL'].sum()
        total_biometria = df_prof_pb['QT_ELEITORES_BIOMETRIA'].sum()
        total_deficiencia = df_prof_pb['QT_ELEITORES_DEFICIENCIA'].sum()

        print("\n========================================================")
        print("      PAINEL DEMOGRÁFICO DO ELEITORADO - PARAÍBA        ")
        print("========================================================")
        print(f"Total de Eleitores Aptos (PB): {total_eleitores:>15,.0f}".replace(",", "."))
        print(f"Eleitores com Biometria:       {total_biometria:>15,.0f} | {(total_biometria/total_eleitores)*100:.2f}%".replace(",", "."))
        print(f"Eleitores com Deficiência:     {total_deficiencia:>15,.0f} | {(total_deficiencia/total_eleitores)*100:.2f}%".replace(",", "."))
        print("========================================================\n")

        # 1. Gênero
        df_genero = df_prof_pb.groupby('DS_GENERO')['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_genero['PCT'] = (df_genero['QT_ELEITORES_PERFIL'] / total_eleitores) * 100
        df_genero = df_genero.sort_values(by='QT_ELEITORES_PERFIL', ascending=False)
        
        print("Distribuição por GÊNERO:")
        print("-" * 56)
        for _, row in df_genero.iterrows():
            print(f"{row['DS_GENERO']:<25} | {row['QT_ELEITORES_PERFIL']:>12,.0f} | {row['PCT']:.2f}%".replace(",", "."))
        print("-" * 56 + "\n")

        # 2. Escolaridade
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
        df_escolaridade = df_prof_pb.groupby('DS_GRAU_ESCOLARIDADE')['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_escolaridade['PCT'] = (df_escolaridade['QT_ELEITORES_PERFIL'] / total_eleitores) * 100
        df_escolaridade['DS_GRAU_ESCOLARIDADE'] = pd.Categorical(df_escolaridade['DS_GRAU_ESCOLARIDADE'], categories=ordem_escolaridade, ordered=True)
        df_escolaridade = df_escolaridade.sort_values('DS_GRAU_ESCOLARIDADE')

        print("Distribuição por GRAU DE ESCOLARIDADE:")
        print("-" * 56)
        for _, row in df_escolaridade.iterrows():
            print(f"{str(row['DS_GRAU_ESCOLARIDADE']):<30} | {row['QT_ELEITORES_PERFIL']:>12,.0f} | {row['PCT']:.2f}%".replace(",", "."))
        print("-" * 56 + "\n")

        # 3. Faixa Etária (Top 10)
        df_idade = df_prof_pb.groupby('DS_FAIXA_ETARIA')['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_idade['PCT'] = (df_idade['QT_ELEITORES_PERFIL'] / total_eleitores) * 100
        df_idade = df_idade.sort_values(by='QT_ELEITORES_PERFIL', ascending=False)
        
        print("Distribuição por FAIXA ETÁRIA (Top 10):")
        print("-" * 56)
        for _, row in df_idade.head(10).iterrows():
            print(f"{row['DS_FAIXA_ETARIA']:<25} | {row['QT_ELEITORES_PERFIL']:>12,.0f} | {row['PCT']:.2f}%".replace(",", "."))
        print("-" * 56 + "\n")

        # 4. Estado Civil
        df_civil = df_prof_pb.groupby('DS_ESTADO_CIVIL')['QT_ELEITORES_PERFIL'].sum().reset_index()
        df_civil['PCT'] = (df_civil['QT_ELEITORES_PERFIL'] / total_eleitores) * 100
        df_civil = df_civil.sort_values(by='QT_ELEITORES_PERFIL', ascending=False)
        
        print("Distribuição por ESTADO CIVIL:")
        print("-" * 56)
        for _, row in df_civil.iterrows():
            print(f"{row['DS_ESTADO_CIVIL']:<25} | {row['QT_ELEITORES_PERFIL']:>12,.0f} | {row['PCT']:.2f}%".replace(",", "."))
        print("-" * 56)
        print("========================================================\n")

        # Salvar tabelas gerais de resumo em um CSV consolidado
        output_file = 'perfil_geral_eleitores_pb_2022.csv'
        with open(output_file, 'w', encoding='utf-8') as f_out:
            f_out.write("=== DADOS GERAIS DO ELEITORADO ===\n")
            f_out.write(f"Total de Eleitores;{total_eleitores}\n")
            f_out.write(f"Com Biometria;{total_biometria}\n")
            f_out.write(f"Com Deficiencia;{total_deficiencia}\n\n")
            
            f_out.write("=== DISTRIBUICAO POR GENERO ===\n")
            df_genero.to_csv(f_out, sep=';', index=False)
            f_out.write("\n=== DISTRIBUICAO POR ESCOLARIDADE ===\n")
            df_escolaridade.to_csv(f_out, sep=';', index=False)
            f_out.write("\n=== DISTRIBUICAO POR FAIXA ETARIA ===\n")
            df_idade.to_csv(f_out, sep=';', index=False)
            f_out.write("\n=== DISTRIBUICAO POR ESTADO CIVIL ===\n")
            df_civil.to_csv(f_out, sep=';', index=False)
            
        print(f"-> [Sucesso] Painel demográfico consolidado salvo em '{output_file}'")

        # 4. Carregando dados de Resultados do TSE para consolidação por município
        id_pacote_resultados = "resultados-2022"
        url_pacote_resultados = f"https://dadosabertos.tse.jus.br/api/3/action/package_show?id={id_pacote_resultados}"
        
        print("\n4. Carregando dados de Resultados do TSE para consolidação por município...")
        resposta_res = requests.get(url_pacote_resultados, headers=headers)
        resposta_res.raise_for_status()
        recursos_res = resposta_res.json()['result']['resources']
        
        url_zip_votos = None
        url_zip_detalhe = None
        
        for r in recursos_res:
            nome_recurso = r.get('name', '').lower()
            url_link = r.get('url', '').lower()
            if 'votação nominal por município e zona' in nome_recurso or 'votacao_nominal_municipio_zona' in url_link:
                url_zip_votos = r['url']
            elif 'detalhe da apuração por município e zona' in nome_recurso or 'detalhe_votacao_munzona' in url_link:
                url_zip_detalhe = r['url']

        zip_local_votos = "votacao_nominal_2022.zip"
        if os.path.exists(zip_local_votos):
            print("   -> Carregando arquivo de Votação Nominal do cache local...")
        else:
            print("   -> Baixando arquivo de Votação Nominal...")
            conteudo_zip_votos = requests.get(url_zip_votos, headers=headers).content
            with open(zip_local_votos, 'wb') as lf:
                lf.write(conteudo_zip_votos)
                
        zip_local_detalhe = "detalhe_votacao_munzona_2022.zip"
        if os.path.exists(zip_local_detalhe):
            print("   -> Carregando arquivo de Detalhe da Apuração do cache local...")
        else:
            print("   -> Baixando arquivo de Detalhe da Apuração...")
            conteudo_zip_detalhe = requests.get(url_zip_detalhe, headers=headers).content
            with open(zip_local_detalhe, 'wb') as lf:
                lf.write(conteudo_zip_detalhe)

        print("\n5. Consolidando votação por município (Presidente e Governador)...")
        z_nom = zipfile.ZipFile(zip_local_votos)
        z_det = zipfile.ZipFile(zip_local_detalhe)

        # Presidente
        arq_br = [arq for arq in z_nom.namelist() if 'BR.csv' in arq.upper() or '_BR' in arq.upper()][0]
        colunas_nom = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NM_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
        df_pres_nom = pd.read_csv(z_nom.open(arq_br), sep=';', encoding='iso-8859-1', usecols=colunas_nom)
        df_pres_nom.columns = df_pres_nom.columns.str.strip()
        df_pres_nom['DS_CARGO'] = df_pres_nom['DS_CARGO'].str.strip()
        df_pres_nom['NM_URNA_CANDIDATO'] = df_pres_nom['NM_URNA_CANDIDATO'].str.strip()
        df_pres_nom['SG_UF'] = df_pres_nom['SG_UF'].str.strip()
        df_pres_filtrado = df_pres_nom[(df_pres_nom['NR_TURNO'] == 1) & (df_pres_nom['DS_CARGO'].str.lower() == 'presidente') & (df_pres_nom['SG_UF'] == 'PB')]

        arq_det_br = [arq for arq in z_det.namelist() if 'BR.csv' in arq.upper() or '_BR' in arq.upper()][0]
        colunas_det = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'CD_MUNICIPIO', 'NM_MUNICIPIO', 'NR_ZONA', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
        df_pres_det_raw = pd.read_csv(z_det.open(arq_det_br), sep=';', encoding='iso-8859-1', usecols=colunas_det)
        df_pres_det_raw.columns = df_pres_det_raw.columns.str.strip()
        df_pres_det_raw['DS_CARGO'] = df_pres_det_raw['DS_CARGO'].str.strip()
        df_pres_det_raw['SG_UF'] = df_pres_det_raw['SG_UF'].str.strip()
        df_pres_det = df_pres_det_raw[(df_pres_det_raw['NR_TURNO'] == 1) & (df_pres_det_raw['DS_CARGO'].str.lower() == 'presidente') & (df_pres_det_raw['SG_UF'] == 'PB')]

        # Governador
        arq_pb = [arq for arq in z_nom.namelist() if 'PB.csv' in arq.upper() or '_PB' in arq.upper()][0]
        df_gov_nom = pd.read_csv(z_nom.open(arq_pb), sep=';', encoding='iso-8859-1', usecols=colunas_nom)
        df_gov_nom.columns = df_gov_nom.columns.str.strip()
        df_gov_nom['DS_CARGO'] = df_gov_nom['DS_CARGO'].str.strip()
        df_gov_nom['NM_URNA_CANDIDATO'] = df_gov_nom['NM_URNA_CANDIDATO'].str.strip()
        df_gov_filtrado = df_gov_nom[(df_gov_nom['NR_TURNO'] == 1) & (df_gov_nom['DS_CARGO'].str.lower() == 'governador')]

        arq_pb_det = [arq for arq in z_det.namelist() if 'PB.csv' in arq.upper() or '_PB' in arq.upper()][0]
        df_gov_det_raw = pd.read_csv(z_det.open(arq_pb_det), sep=';', encoding='iso-8859-1', usecols=colunas_det)
        df_gov_det_raw.columns = df_gov_det_raw.columns.str.strip()
        df_gov_det_raw['DS_CARGO'] = df_gov_det_raw['DS_CARGO'].str.strip()
        df_gov_det = df_gov_det_raw[(df_gov_det_raw['NR_TURNO'] == 1) & (df_gov_det_raw['DS_CARGO'].str.lower() == 'governador')]

        # Definir as bases completas de votos por zona/município para escolaridade municipal
        df_pres_brancos_all = df_pres_det.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_VOTOS_BRANCOS'].sum().reset_index()
        df_pres_brancos_all.rename(columns={'QT_VOTOS_BRANCOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_pres_brancos_all['NM_URNA_CANDIDATO'] = 'VOTO BRANCO'

        df_pres_nulos_all = df_pres_det.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_TOTAL_VOTOS_NULOS'].sum().reset_index()
        df_pres_nulos_all.rename(columns={'QT_TOTAL_VOTOS_NULOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_pres_nulos_all['NM_URNA_CANDIDATO'] = 'VOTO NULO'

        df_votos_all_pres = pd.concat([
            df_pres_filtrado[['CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']],
            df_pres_brancos_all,
            df_pres_nulos_all
        ], ignore_index=True)

        df_gov_brancos_all = df_gov_det.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_VOTOS_BRANCOS'].sum().reset_index()
        df_gov_brancos_all.rename(columns={'QT_VOTOS_BRANCOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_gov_brancos_all['NM_URNA_CANDIDATO'] = 'VOTO BRANCO'

        df_gov_nulos_all = df_gov_det.groupby(['CD_MUNICIPIO', 'NR_ZONA'])['QT_TOTAL_VOTOS_NULOS'].sum().reset_index()
        df_gov_nulos_all.rename(columns={'QT_TOTAL_VOTOS_NULOS': 'QT_VOTOS_NOMINAIS'}, inplace=True)
        df_gov_nulos_all['NM_URNA_CANDIDATO'] = 'VOTO NULO'

        df_votos_all_gov = pd.concat([
            df_gov_filtrado[['CD_MUNICIPIO', 'NR_ZONA', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']],
            df_gov_brancos_all,
            df_gov_nulos_all
        ], ignore_index=True)

        # Agregar Detalhes por Município
        df_pres_det_mun = df_pres_det.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO'])[['QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']].sum().reset_index()
        df_pres_det_mun.rename(columns={
            'QT_APTOS': 'PRES_APTOS',
            'QT_COMPARECIMENTO': 'PRES_COMPARECIMENTO',
            'QT_ABSTENCOES': 'PRES_ABSTENCOES',
            'QT_VOTOS_BRANCOS': 'PRES_VOTOS_BRANCOS',
            'QT_TOTAL_VOTOS_NULOS': 'PRES_VOTOS_NULOS'
        }, inplace=True)

        df_gov_det_mun = df_gov_det.groupby(['CD_MUNICIPIO', 'NM_MUNICIPIO'])[['QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']].sum().reset_index()
        df_gov_det_mun.rename(columns={
            'QT_APTOS': 'GOV_APTOS',
            'QT_COMPARECIMENTO': 'GOV_COMPARECIMENTO',
            'QT_ABSTENCOES': 'GOV_ABSTENCOES',
            'QT_VOTOS_BRANCOS': 'GOV_VOTOS_BRANCOS',
            'QT_TOTAL_VOTOS_NULOS': 'GOV_VOTOS_NULOS'
        }, inplace=True)

        # Pivotar Votos de Candidatos
        df_pres_pivot = df_pres_filtrado.pivot_table(index=['CD_MUNICIPIO', 'NM_MUNICIPIO'], columns='NM_URNA_CANDIDATO', values='QT_VOTOS_NOMINAIS', aggfunc='sum', fill_value=0)
        df_pres_pivot.columns = ['PRES_VOTOS_' + str(c) for c in df_pres_pivot.columns]
        df_pres_pivot = df_pres_pivot.reset_index()

        df_gov_pivot = df_gov_filtrado.pivot_table(index=['CD_MUNICIPIO', 'NM_MUNICIPIO'], columns='NM_URNA_CANDIDATO', values='QT_VOTOS_NOMINAIS', aggfunc='sum', fill_value=0)
        df_gov_pivot.columns = ['GOV_VOTOS_' + str(c) for c in df_gov_pivot.columns]
        df_gov_pivot = df_gov_pivot.reset_index()

        # Mesclar tudo em um DataFrame único consolidado de Municípios
        df_consolidado = pd.merge(df_pres_det_mun, df_pres_pivot, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'], how='outer')
        df_consolidado = pd.merge(df_consolidado, df_gov_det_mun, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'], how='outer')
        df_consolidado = pd.merge(df_consolidado, df_gov_pivot, on=['CD_MUNICIPIO', 'NM_MUNICIPIO'], how='outer')

        # Salvar banco de dados detalhado por município
        consolidado_file = 'resultado_consolidado_municipios_pb_2022.csv'
        df_consolidado.to_csv(consolidado_file, sep=';', index=False)
        print(f"-> [Sucesso] Resultados por município salvos com sucesso em '{consolidado_file}'")

        # 6. Busca de cidade específica (por argumento ou busca interativa)
        import sys
        
        def exibir_dados_cidade(busca_nome):
            busca_nome = busca_nome.strip().upper()
            cidades_encontradas = df_dem_mun[df_dem_mun['NM_MUNICIPIO'].str.upper() == busca_nome]
            
            if cidades_encontradas.empty:
                sugestoes = df_dem_mun[df_dem_mun['NM_MUNICIPIO'].str.upper().str.contains(busca_nome, na=False)]['NM_MUNICIPIO'].tolist()
                print(f"\n❌ Cidade '{busca_nome}' não encontrada.")
                if sugestoes:
                    print(f"Você quis dizer: {', '.join(sugestoes[:5])}?")
                return
                
            row_dem = cidades_encontradas.iloc[0]
            cid_nome = row_dem['NM_MUNICIPIO']
            cid_cod = row_dem['CD_MUNICIPIO']
            
            # Imprimir Painel Demográfico
            print(f"\n========================================================")
            print(f"   PAINEL DEMOGRÁFICO DO ELEITORADO: {cid_nome} (PB)   ")
            print(f"========================================================")
            print(f"Total de Eleitores Aptos: {row_dem['TOTAL_ELEITORES']:,.0f}".replace(",", "."))
            print(f"Biometria Cadastrada:     {row_dem['BIOMETRIA_PCT']:.2f}%")
            print(f"Eleitores com Deficiência: {row_dem['DEFICIENCIA_PCT']:.2f}%")
            print(f"Gênero Feminino:          {row_dem['GENERO_FEMININO_PCT']:.2f}%")
            print(f"Gênero Masculino:         {row_dem['GENERO_MASCULINO_PCT']:.2f}%")
            
            print(f"\nGrau de Escolaridade:")
            city_edu_cols = [c for c in df_dem_mun.columns if c.startswith('ESCOLARIDADE_')]
            city_edu_vals = {c.replace('ESCOLARIDADE_', '').replace('_PCT', ''): row_dem[c] for c in city_edu_cols}
            for edu_cat, edu_val in sorted(city_edu_vals.items(), key=lambda x: x[1], reverse=True):
                if edu_val > 0:
                    print(f"  * {edu_cat:<30}: {edu_val:.2f}%")
            print("========================================================\n")
            
            # Imprimir Votação
            row_votos = df_consolidado[df_consolidado['CD_MUNICIPIO'] == cid_cod]
            if not row_votos.empty:
                r_v = row_votos.iloc[0]
                print(f"========================================================")
                print(f"   APURAÇÃO DE VOTOS EM {cid_nome} (1º TURNO 2022)   ")
                print(f"========================================================")
                print("PRESIDENTE DA REPÚBLICA:")
                print(f"  - Comparecimento: {r_v['PRES_COMPARECIMENTO']:,.0f} | Abstenção: {r_v['PRES_ABSTENCOES']:,.0f}".replace(",", "."))
                print(f"  - Brancos: {r_v['PRES_VOTOS_BRANCOS']:,.0f} | Nulos: {r_v['PRES_VOTOS_NULOS']:,.0f}".replace(",", "."))
                
                pres_cols = [c for c in df_consolidado.columns if c.startswith('PRES_VOTOS_') and c not in ['PRES_VOTOS_BRANCOS', 'PRES_VOTOS_NULOS']]
                pres_votes = {c.replace('PRES_VOTOS_', ''): r_v[c] for c in pres_cols if r_v[c] > 0}
                for cand_nome, cand_votos in sorted(pres_votes.items(), key=lambda x: x[1], reverse=True):
                    print(f"  * {cand_nome:<22}: {cand_votos:>8,.0f} votos".replace(",", "."))
                    
                print("\nGOVERNADOR DO ESTADO:")
                print(f"  - Comparecimento: {r_v['GOV_COMPARECIMENTO']:,.0f} | Abstenção: {r_v['GOV_ABSTENCOES']:,.0f}".replace(",", "."))
                print(f"  - Brancos: {r_v['GOV_VOTOS_BRANCOS']:,.0f} | Nulos: {r_v['GOV_VOTOS_NULOS']:,.0f}".replace(",", "."))
                
                gov_cols = [c for c in df_consolidado.columns if c.startswith('GOV_VOTOS_') and c not in ['GOV_VOTOS_BRANCOS', 'GOV_VOTOS_NULOS']]
                gov_votes = {c.replace('GOV_VOTOS_', ''): r_v[c] for c in gov_cols if r_v[c] > 0}
                for cand_nome, cand_votos in sorted(gov_votes.items(), key=lambda x: x[1], reverse=True):
                    print(f"  * {cand_nome:<22}: {cand_votos:>8,.0f} votos".replace(",", "."))
                print("========================================================\n")

                # --- Escolaridade dos Eleitores por Presidente na Cidade ---
                df_merged_pres_cid = pd.merge(df_votos_all_pres[df_votos_all_pres['CD_MUNICIPIO'] == cid_cod], df_prof_frac[df_prof_frac['CD_MUNICIPIO'] == cid_cod], on=['CD_MUNICIPIO', 'NR_ZONA'])
                df_merged_pres_cid['ESTIMATED_VOTES'] = df_merged_pres_cid['QT_VOTOS_NOMINAIS'] * df_merged_pres_cid['FRACTION']
                
                df_cand_edu_pres_cid = df_merged_pres_cid.groupby(['NM_URNA_CANDIDATO', 'DS_GRAU_ESCOLARIDADE'])['ESTIMATED_VOTES'].sum().reset_index()
                df_cand_total_pres_cid = df_merged_pres_cid.groupby(['NM_URNA_CANDIDATO'])['ESTIMATED_VOTES'].sum().reset_index(name='TOTAL_ESTIMATED')
                df_result_pres_cid = pd.merge(df_cand_edu_pres_cid, df_cand_total_pres_cid, on=['NM_URNA_CANDIDATO'])
                df_result_pres_cid['PCT'] = (df_result_pres_cid['ESTIMATED_VOTES'] / df_result_pres_cid['TOTAL_ESTIMATED']) * 100
                
                df_pivot_pres_cid = df_result_pres_cid.pivot(index='DS_GRAU_ESCOLARIDADE', columns='NM_URNA_CANDIDATO', values='PCT')
                df_pivot_pres_cid = df_pivot_pres_cid.reindex(ordem_escolaridade)
                
                # Selecionar os 5 principais candidatos/opções da cidade
                top_cands_pres_cid = df_votos_all_pres[df_votos_all_pres['CD_MUNICIPIO'] == cid_cod].groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index().sort_values(by='QT_VOTOS_NOMINAIS', ascending=False).head(5)['NM_URNA_CANDIDATO'].tolist()
                present_cols_pres_cid = [c for c in top_cands_pres_cid if c in df_pivot_pres_cid.columns]
                df_pivot_subset_pres_cid = df_pivot_pres_cid[present_cols_pres_cid]
                
                print(f"========================================================")
                print(f"   ESCOLARIDADE DOS ELEITORES POR PRESIDENTE EM {cid_nome}  ")
                print(f"========================================================")
                headers_str_pres = f"{'Grau de Escolaridade':<30}"
                for col in present_cols_pres_cid:
                    short_col = col[:12]
                    headers_str_pres += f" | {short_col:>12}"
                print(headers_str_pres)
                print("-" * len(headers_str_pres))
                
                for idx, row in df_pivot_subset_pres_cid.iterrows():
                    row_str = f"{idx:<30}"
                    for col in present_cols_pres_cid:
                        val = row[col]
                        val_str = f"{val:.2f}%" if not pd.isna(val) else "0.00%"
                        row_str += f" | {val_str:>12}"
                    print(row_str.replace(",", "."))
                print("========================================================\n")

                # --- Escolaridade dos Eleitores por Governador na Cidade ---
                df_merged_gov_cid = pd.merge(df_votos_all_gov[df_votos_all_gov['CD_MUNICIPIO'] == cid_cod], df_prof_frac[df_prof_frac['CD_MUNICIPIO'] == cid_cod], on=['CD_MUNICIPIO', 'NR_ZONA'])
                df_merged_gov_cid['ESTIMATED_VOTES'] = df_merged_gov_cid['QT_VOTOS_NOMINAIS'] * df_merged_gov_cid['FRACTION']
                
                df_cand_edu_gov_cid = df_merged_gov_cid.groupby(['NM_URNA_CANDIDATO', 'DS_GRAU_ESCOLARIDADE'])['ESTIMATED_VOTES'].sum().reset_index()
                df_cand_total_gov_cid = df_merged_gov_cid.groupby(['NM_URNA_CANDIDATO'])['ESTIMATED_VOTES'].sum().reset_index(name='TOTAL_ESTIMATED')
                df_result_gov_cid = pd.merge(df_cand_edu_gov_cid, df_cand_total_gov_cid, on=['NM_URNA_CANDIDATO'])
                df_result_gov_cid['PCT'] = (df_result_gov_cid['ESTIMATED_VOTES'] / df_result_gov_cid['TOTAL_ESTIMATED']) * 100
                
                df_pivot_gov_cid = df_result_gov_cid.pivot(index='DS_GRAU_ESCOLARIDADE', columns='NM_URNA_CANDIDATO', values='PCT')
                df_pivot_gov_cid = df_pivot_gov_cid.reindex(ordem_escolaridade)
                
                # Selecionar os 5 principais candidatos/opções da cidade
                top_cands_gov_cid = df_votos_all_gov[df_votos_all_gov['CD_MUNICIPIO'] == cid_cod].groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index().sort_values(by='QT_VOTOS_NOMINAIS', ascending=False).head(5)['NM_URNA_CANDIDATO'].tolist()
                present_cols_gov_cid = [c for c in top_cands_gov_cid if c in df_pivot_gov_cid.columns]
                df_pivot_subset_gov_cid = df_pivot_gov_cid[present_cols_gov_cid]
                
                print(f"========================================================")
                print(f"   ESCOLARIDADE DOS ELEITORES POR GOVERNADOR EM {cid_nome}  ")
                print(f"========================================================")
                headers_str_gov = f"{'Grau de Escolaridade':<30}"
                for col in present_cols_gov_cid:
                    short_col = col[:12]
                    headers_str_gov += f" | {short_col:>12}"
                print(headers_str_gov)
                print("-" * len(headers_str_gov))
                
                for idx, row in df_pivot_subset_gov_cid.iterrows():
                    row_str = f"{idx:<30}"
                    for col in present_cols_gov_cid:
                        val = row[col]
                        val_str = f"{val:.2f}%" if not pd.isna(val) else "0.00%"
                        row_str += f" | {val_str:>12}"
                    print(row_str.replace(",", "."))
                print("========================================================\n")

        # Executar exibição por argumento do terminal ou entrar no loop interativo
        if len(sys.argv) > 1:
            busca_arg = " ".join(sys.argv[1:])
            exibir_dados_cidade(busca_arg)
        elif sys.stdin.isatty():
            print("\n" + "=" * 56)
            print("         CONSULTA INTERATIVA DE MUNICÍPIOS (PB)         ")
            print("=" * 56)
            while True:
                busca = input("\nDigite o nome da cidade que deseja visualizar (ou Enter para sair): ").strip()
                if not busca:
                    print("Saindo...")
                    break
                exibir_dados_cidade(busca)

    else:
        print("Não foi possível localizar o link do Perfil do Eleitorado na API do TSE.")

except Exception as e:
    print(f"\nOcorreu um erro no processamento do eleitorado geral: {e}")
