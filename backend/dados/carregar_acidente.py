#script para baixar, limpar, transformar e carregar dados de acidentes com animais peçonhentos no estado de São Paulo
import pandas as pd
from sqlalchemy import create_engine
from pysus.online_data.SINAN import SINAN

# --- CONFIGURAÇÃO ---
ANOS_PARA_BAIXAR = range(2007,2026) 
CODIGO_DOENCA = 'ANIM'
CODIGO_UF_SP = 35
ARQUIVO_MUNICIPIOS = 'municipios_SP.csv'

# Configurações do banco de dados
nome_banco_dados = 'sinan.db'
nome_tabela_acidentes = 'acidentes'

print(f"--- INICIANDO PIPELINE DE DADOS DE ACIDENTES ---")

try:
    # PASSO 1: CRIAR O "DICIONÁRIO" DE MUNICÍPIOS PARA ENRIQUECIMENTO
    print(f"Carregando dicionário de municípios de '{ARQUIVO_MUNICIPIOS}'...")
    df_municipios = pd.read_csv(ARQUIVO_MUNICIPIOS)
    df_municipios['chave_municipio_6_digitos'] = (df_municipios['codigo_ibge'] / 10).astype(int)
    mapa_municipios = pd.Series(df_municipios.nome.values, index=df_municipios.chave_municipio_6_digitos).to_dict()
    print("✅ Dicionário de municípios criado.")

    # PASSO 2: BAIXAR DADOS BRUTOS DO SINAN COM PYSUS
    print("\nConectando ao SINAN para baixar dados de acidentes...")
    sinan = SINAN().load()
    lista_dataframes_anuais = []
    for ano in ANOS_PARA_BAIXAR:
        print(f"\nBuscando dados para o ano {ano}...")
        arquivos = sinan.get_files(dis_code=CODIGO_DOENCA, year=ano)
        if arquivos:
            arquivo_para_baixar = arquivos[0]
            print(f"Baixando {arquivo_para_baixar.name}...")
            parquet_obj = arquivo_para_baixar.download(local_dir="dados_brutos")
            df_ano_bruto = parquet_obj.to_dataframe()
            print(f"Download de {ano} concluído. {len(df_ano_bruto)} registros baixados para o Brasil.")
            
            # Filtra apenas registros de São Paulo
            coluna_uf_limpa = df_ano_bruto['SG_UF_NOT'].str.strip()
            coluna_uf_numerica = pd.to_numeric(coluna_uf_limpa, errors='coerce')
            df_ano_sp = df_ano_bruto[coluna_uf_numerica == CODIGO_UF_SP].copy()

            if not df_ano_sp.empty:
                lista_dataframes_anuais.append(df_ano_sp)
                print(f"✅ {len(df_ano_sp)} registros de São Paulo para o ano {ano} encontrados.")
    
    if not lista_dataframes_anuais:
        raise ValueError("Nenhum dado de acidentes foi encontrado para os anos/estado selecionados.")
        
    df_completo = pd.concat(lista_dataframes_anuais, ignore_index=True)
    print(f"\nDataFrame completo criado com {len(df_completo)} registros totais.")

    # PASSO 3: LIMPEZA, TRANSFORMAÇÃO E ENRIQUECIMENTO
    print("\nIniciando limpeza e transformação dos dados...")

    # Seleciona as colunas de interesse do dado bruto
    colunas_para_trabalhar = {
        'ANT_DT_ACI': 'data_acidente',
        'ANT_MUNIC_': 'id_municipio_acidente',
        'NU_IDADE_N': 'idade',
        'CS_SEXO': 'sexo',
        'TP_ACIDENT': 'tipo_animal',
        'TRA_CLASSI': 'classificacao_caso',
        'EVOLUCAO': 'evolucao_caso'
    }
    df_limpo = df_completo[colunas_para_trabalhar.keys()].copy()
    df_limpo.rename(columns=colunas_para_trabalhar, inplace=True)
    
    # Enriquecimento: Adiciona o nome do município usando o dicionário
    df_limpo['id_municipio_acidente'] = pd.to_numeric(df_limpo['id_municipio_acidente'], errors='coerce')
    df_limpo['cidade_acidente'] = df_limpo['id_municipio_acidente'].map(mapa_municipios)

    # "Tradução" dos códigos para textos
    mapa_animal = {1.0: 'Serpente', 2.0: 'Aranha', 3.0: 'Escorpião', 4.0: 'Lagarta', 5.0: 'Abelha', 6.0: 'Outros', 9.0: 'Ignorado'}
    df_limpo['tipo_animal'] = pd.to_numeric(df_limpo['tipo_animal'], errors='coerce').map(mapa_animal)
    
    mapa_classificacao = {1.0: 'Leve', 2.0: 'Moderado', 3.0: 'Grave', 9.0: 'Ignorado'}
    df_limpo['classificacao_caso'] = pd.to_numeric(df_limpo['classificacao_caso'], errors='coerce').map(mapa_classificacao)
    
    mapa_evolucao = {1.0: 'Cura', 2.0: 'Óbito pelo Acidente', 3.0: 'Óbito por Outras Causas', 9.0: 'Ignorado'}
    df_limpo['evolucao_caso'] = pd.to_numeric(df_limpo['evolucao_caso'], errors='coerce').map(mapa_evolucao)
    
    mapa_sexo = {'M': 'Masculino', 'F': 'Feminino', 'I': 'Ignorado'}
    df_limpo['sexo'] = df_limpo['sexo'].astype(str).str.strip().map(mapa_sexo)
    
    # Conversão de datas e tipos numéricos
    df_limpo['data_acidente'] = pd.to_datetime(df_limpo['data_acidente'], errors='coerce', format='%Y%m%d')
    df_limpo.dropna(subset=['id_municipio_acidente'], inplace=True)
    df_limpo['id_municipio_acidente'] = df_limpo['id_municipio_acidente'].astype(int)

    print("✅ Limpeza e transformação finalizadas.")
    
    # PASSO 4: CARREGAR OS DADOS FINAIS NO BANCO DE DADOS
    print(f"\nCarregando dados limpos para a tabela '{nome_tabela_acidentes}'...")
    engine = create_engine(f'sqlite:///{nome_banco_dados}')
    df_limpo.to_sql(
        nome_tabela_acidentes,
        con=engine,
        if_exists='replace',
        index=True,
        index_label='id'
    )
    print("\n✅✅✅ PIPELINE DE ACIDENTES CONCLUÍDO COM SUCESSO! ✅✅✅")

except Exception as e:
    print(f"\n❌ ERRO: Ocorreu um problema no pipeline: {e}")