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

print("1. Acessando a API de Recursos do TSE...")

try:
    resposta = requests.get(url_pacote, headers=headers)
    resposta.raise_for_status()
    recursos = resposta.json()['result']['resources']
    
    url_zip = None
    url_zip_detalhe = None
    
    # Procura pelos arquivos corretos de Votação Nominal e Detalhe da Apuração
    for r in recursos:
        nome_recurso = r.get('name', '').lower()
        url_link = r.get('url', '').lower()
        if 'votação nominal por município e zona' in nome_recurso or 'votacao_nominal_municipio_zona' in url_link:
            url_zip = r['url']
        elif 'detalhe da apuração por município e zona' in nome_recurso or 'detalhe_votacao_munzona' in url_link:
            url_zip_detalhe = r['url']

    if url_zip and url_zip_detalhe:
        # --- PARTE A: CARREGAMENTO DOS VOTOS NOMINAIS ---
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
            
        # --- PARTE B: CARREGAMENTO DO DETALHE DA APURAÇÃO ---
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

        # --- PARTE C: PROCESSAMENTO DOS VOTOS DOS CANDIDATOS ---
        with zipfile.ZipFile(io.BytesIO(conteudo_zip)) as z:
            arquivos_internos = z.namelist()
            arq_pb = [arq for arq in arquivos_internos if 'PB.csv' in arq.upper() or '_PB' in arq.upper()]
            
            if arq_pb:
                arq_pb = arq_pb[0]
                print(f"3. Filtrando e processando o arquivo da Paraíba (Votos Nominais): {arq_pb}")
                
                with z.open(arq_pb) as f:
                    colunas_nominais = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'NM_URNA_CANDIDATO', 'QT_VOTOS_NOMINAIS']
                    df = pd.read_csv(f, sep=';', encoding='iso-8859-1', usecols=colunas_nominais)
                    
                    df.columns = df.columns.str.strip()
                    df['DS_CARGO'] = df['DS_CARGO'].str.strip()
                    df['NM_URNA_CANDIDATO'] = df['NM_URNA_CANDIDATO'].str.strip()
                    
                    # Filtra apenas 1º turno e cargo de Governador
                    df_filtrado = df[(df['NR_TURNO'] == 1) & (df['DS_CARGO'].str.lower() == 'governador')]
                    placar_cands = df_filtrado.groupby('NM_URNA_CANDIDATO')['QT_VOTOS_NOMINAIS'].sum().reset_index()
                    placar_cands.columns = ['NM_VOTAVEL', 'QT_VOTOS']
            else:
                raise FileNotFoundError("Não encontramos o arquivo da PB dentro do ZIP de Votação Nominal.")

        # --- PARTE D: PROCESSAMENTO DE PARTICIPAÇÃO, BRANCOS E NULOS ---
        with zipfile.ZipFile(io.BytesIO(conteudo_zip_detalhe)) as z_det:
            arquivos_internos_det = z_det.namelist()
            arq_pb_det = [arq for arq in arquivos_internos_det if 'PB.csv' in arq.upper() or '_PB' in arq.upper()]
            
            if arq_pb_det:
                arq_pb_det = arq_pb_det[0]
                print(f"4. Filtrando e processando o arquivo da Paraíba (Detalhe da Apuração): {arq_pb_det}")
                
                with z_det.open(arq_pb_det) as f_det:
                    colunas_detalhe = ['NR_TURNO', 'SG_UF', 'DS_CARGO', 'QT_APTOS', 'QT_COMPARECIMENTO', 'QT_ABSTENCOES', 'QT_VOTOS_BRANCOS', 'QT_TOTAL_VOTOS_NULOS']
                    df_det = pd.read_csv(f_det, sep=';', encoding='iso-8859-1', usecols=colunas_detalhe)
                    
                    df_det.columns = df_det.columns.str.strip()
                    df_det['DS_CARGO'] = df_det['DS_CARGO'].str.strip()
                    
                    # Filtra apenas 1º turno e cargo de Governador
                    df_det_filtrado = df_det[(df_det['NR_TURNO'] == 1) & (df_det['DS_CARGO'].str.lower() == 'governador')]
                    
                    votos_aptos = df_det_filtrado['QT_APTOS'].sum()
                    votos_comparecimento = df_det_filtrado['QT_COMPARECIMENTO'].sum()
                    votos_abstencoes = df_det_filtrado['QT_ABSTENCOES'].sum()
                    votos_brancos = df_det_filtrado['QT_VOTOS_BRANCOS'].sum()
                    votos_nulos = df_det_filtrado['QT_TOTAL_VOTOS_NULOS'].sum()
            else:
                raise FileNotFoundError("Não encontramos o arquivo da PB dentro do ZIP de Detalhe da Apuração.")

        # --- PARTE E: UNIÃO E APRESENTAÇÃO DOS RESULTADOS ---
        # Cria registros de Brancos e Nulos
        df_brancos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO BRANCO', 'QT_VOTOS': votos_brancos}])
        df_nulos = pd.DataFrame([{'NM_VOTAVEL': 'VOTO NULO', 'QT_VOTOS': votos_nulos}])
        
        # Consolida a tabela final
        placar = pd.concat([placar_cands, df_brancos, df_nulos], ignore_index=True)
        placar = placar.sort_values(by='QT_VOTOS', ascending=False).reset_index(drop=True)
        
        # Print do Bloco de Participação e Abstenção
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
            
            # Regra da porcentagem: candidatos sobre válidos, brancos/nulos sobre o total
            if nome in ['VOTO BRANCO', 'VOTO NULO']:
                pct = (votos / total_votos_apurados) * 100
                tipo = "s/ Total"
            else:
                pct = (votos / votos_validos) * 100
                tipo = "s/ Válidos"
                
            print(f"{nome:<25} | {votos:>15,.0f} | {pct:.2f}% {tipo}".replace(",", "."))
        
        print("========================================================")
        
        # Salva o arquivo final estruturado no seu repositório do Hackathon
        placar.to_csv("resultado_governador_pb_2022.csv", index=False, sep=";")
        print("\nArquivo 'resultado_governador_pb_2022.csv' gerado com sucesso!")
        
    else:
        print("Não foi possível localizar os links de Votação Nominal ou Detalhe da Apuração na API.")

except Exception as e:
    print(f"\nErro no processamento: {e}")