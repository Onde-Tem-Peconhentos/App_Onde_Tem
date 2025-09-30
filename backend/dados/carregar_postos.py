#scritp para carregar dados de postos de saúde de um arquivo CSV para um banco de dados SQLite
import pandas as pd
from sqlalchemy import create_engine

# --- CONFIGURAÇÃO ---
arquivo_entrada = 'postos_geral.csv'
nome_banco_dados = 'sinan.db'
nome_tabela = 'postos_saude'

print(f"--- Iniciando: Carregando tabela '{nome_tabela}' ---")

try:
    df_postos = pd.read_csv(arquivo_entrada)

    # 1. Seleção e renomeação das colunas
    colunas_finais = {
        'Unidade de Saúde': 'nome',
        'Cidade': 'municipio',
        'Endereço': 'endereco',
        'Telefone': 'telefone',
        'latitude': 'latitude',
        'longitude': 'longitude',
        '24h': 'atendimento_24h'
    }
    df_final = df_postos[colunas_finais.keys()].copy()
    df_final.rename(columns=colunas_finais, inplace=True)

    # 2. Correção de tipos de dados
    df_final['latitude'] = pd.to_numeric(df_final['latitude'], errors='coerce')
    df_final['atendimento_24h'] = pd.to_numeric(df_final['atendimento_24h'], errors='coerce')

    # 3. Carga para o banco de dados com chave primária 'id'
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