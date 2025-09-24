import pandas as pd
from sqlalchemy import create_engine

# --- CONFIGURAÇÃO ---
arquivo_entrada = 'municipios_SP.csv'
nome_banco_dados = 'sinan.db'
nome_tabela = 'municipios'

print(f"--- Iniciando: Carregando tabela '{nome_tabela}' ---")

try:
    df_municipios = pd.read_csv(arquivo_entrada)

    # 1. Seleção e renomeação das colunas
    colunas_finais = {
        'codigo_ibge': 'codigo_ibge',
        'nome': 'nome',
        'latitude': 'latitude',
        'longitude': 'longitude'
    }
    df_final = df_municipios[colunas_finais.keys()].copy()
    df_final.rename(columns=colunas_finais, inplace=True)
    
    # 2. Carga para o banco de dados com chave primária 'id'
    engine = create_engine(f'sqlite:///{nome_banco_dados}')
    df_final.to_sql(
        nome_tabela,
        con=engine,
        if_exists='replace',
        index=False,
        
    )
    print(f"✅ Tabela '{nome_tabela}' carregada com sucesso!")

except Exception as e:
    print(f"❌ ERRO ao processar a tabela '{nome_tabela}': {e}")