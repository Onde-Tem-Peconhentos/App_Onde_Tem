import pandas as pd
from sqlalchemy import create_engine

# --- CONFIGURAÇÃO ---
arquivo_entrada = 'dados_localizados.csv'
nome_banco_dados = 'sinan.db'
nome_tabela = 'acidentes'

print(f"--- Iniciando: Carregando tabela '{nome_tabela}' ---")

try:
    df = pd.read_csv(arquivo_entrada, low_memory=False)

    # 1. Seleção e renomeação final das colunas
    colunas_finais = {
        'ANT_DT_ACI': 'data_acidente',
        'cid_origem': 'cidade_acidente',
        'lat_origem': 'latitude',
        'lon_origem': 'longitude',
        'NU_IDADE_N': 'idade',
        'CS_SEXO': 'sexo',
        'TP_ACIDENT': 'tipo_animal',
        'TRA_CLASSI': 'classificacao_caso',
        'EVOLUCAO': 'evolucao_caso'
    }
    df_final = df[colunas_finais.keys()].copy()
    df_final.rename(columns=colunas_finais, inplace=True)

    # 2. "Tradução" dos códigos para textos
    mapa_animal = {1.0: 'Serpente', 2.0: 'Aranha', 3.0: 'Escorpião', 4.0: 'Lagarta', 5.0: 'Abelha', 6.0: 'Outros', 9.0: 'Ignorado'}
    df_final['tipo_animal'] = df_final['tipo_animal'].map(mapa_animal)

    mapa_classificacao = {1.0: 'Leve', 2.0: 'Moderado', 3.0: 'Grave', 9.0: 'Ignorado'}
    df_final['classificacao_caso'] = df_final['classificacao_caso'].map(mapa_classificacao)

    mapa_evolucao = {1.0: 'Cura', 2.0: 'Óbito pelo Acidente', 3.0: 'Óbito por Outras Causas', 9.0: 'Ignorado'}
    df_final['evolucao_caso'] = df_final['evolucao_caso'].map(mapa_evolucao)
    
    mapa_sexo = {'M': 'Masculino', 'F': 'Feminino', 'I': 'Ignorado'}
    df_final['sexo'] = df_final['sexo'].map(mapa_sexo)

    # 3. Correção do tipo da coluna de data
    df_final['data_acidente'] = pd.to_datetime(df_final['data_acidente'], errors='coerce')

    # 4. Carga para o banco de dados com chave primária 'id'
    engine = create_engine(f'sqlite:///{nome_banco_dados}')
    df_final.to_sql(
        nome_tabela,
        con=engine,
        if_exists='replace',
        index=True,
        index_label='id'
    )
    print(f"✅ Tabela '{nome_tabela}' carregada com sucesso!")

except Exception as e:
    print(f"❌ ERRO ao processar a tabela '{nome_tabela}': {e}")