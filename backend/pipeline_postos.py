import pandas as pd
import numpy as np
from db import engine
# Importamos o modelo apenas para garantir que a tabela seja criada se não existir
# (Assumindo que você roda um create_all em algum lugar, ou o to_sql cria)
from models import Posto 

def limpar_valor_float(valor):
    """Tenta converter para float, retorna None se falhar"""
    try:
        return float(valor)
    except (ValueError, TypeError):
        return None

def importar_postos():
    print("Lendo arquivo CSV")
    # Lê o CSV. O pandas detecta automaticamente o cabeçalho e tipos.
    df = pd.read_csv("postos_organizados.csv")

    print(f"Total de linhas no CSV: {len(df)}")

    # Vamos criar um DataFrame novo apenas com as colunas que existem no Banco
    df_db = pd.DataFrame()

    # --- Mapeamento: Esquerda (Banco) = Direita (CSV) ---
    
    df_db['municipio_nome'] = df['MUNICIPIO']
    
    # A chave estrangeira principal
    # Convertemos para numérico e forçamos erro se não for número, depois removemos NaNs
    df_db['cod_mun7'] = pd.to_numeric(df['ID_IBGE'], errors='coerce')
    
    df_db['cod_mun6'] = df['ID_MUNICIP']
    df_db['gve'] = df['GVE']
    df_db['ubs'] = df['UNIDADE_DE_SAUDE']
    df_db['endereco'] = df['ENDERECO']
    
    # Campos booleanos/inteiros (0 ou 1)
    df_db['tem_soro'] = pd.to_numeric(df['TEM_SORO'], errors='coerce').fillna(0).astype(int)
    df_db['tipo_soro'] = df['TIPO_SORO']
    df_db['aberto_24h'] = pd.to_numeric(df['24H'], errors='coerce').fillna(0).astype(int)
    df_db['telefone'] = df['TELEFONE']

    # Tratamento de Latitude/Longitude
    # O CSV tem LATITUDE (limpa) e LAT_GOOGLE (às vezes suja/formatada estranho)
    # Tentamos converter 'LATITUDE' primeiro. Se falhar (NaN), tentamos 'LAT_GOOGLE'.
    lat_clean = pd.to_numeric(df['LATITUDE'], errors='coerce')
    lat_google = pd.to_numeric(df['LAT_GOOGLE'], errors='coerce')
    df_db['latitude'] = lat_clean.fillna(lat_google)

    lon_clean = pd.to_numeric(df['LONGITUDE'], errors='coerce')
    lon_google = pd.to_numeric(df['LON_GOOGLE'], errors='coerce')
    df_db['longitude'] = lon_clean.fillna(lon_google)

    # Soros específicos (Flags 0 ou 1)
    cols_soros = {
        'aracnidico': 'ARACNÍDICO',
        'botropico': 'BOTRÓPICO',
        'crotalico': 'CROTÁLICO',
        'elapidico': 'ELAPÍDICO',
        'escorpionico': 'ESCORPIÔNICO',
        'lonomico': 'LONÔMICO'
    }

    for col_db, col_csv in cols_soros.items():
        # Converte para numérico, se der erro vira 0
        df_db[col_db] = pd.to_numeric(df[col_csv], errors='coerce').fillna(0).astype(int)

    # --- Limpeza Final ---
    # Removemos linhas que por acaso não tenham código IBGE (essenciais para a FK)
    linhas_antes = len(df_db)
    df_db = df_db.dropna(subset=['cod_mun7'])
    df_db['cod_mun7'] = df_db['cod_mun7'].astype(int)
    
    if len(df_db) < linhas_antes:
        print(f"Aviso: {linhas_antes - len(df_db)} linhas removidas por falta de Código IBGE.")

    print("Iniciando inserção no Banco de Dados...")
    
    try:
        # if_exists='append' adiciona os dados sem apagar a tabela
        # index=False para não enviar o índice do Pandas como coluna
        df_db.to_sql('postos', con=engine, if_exists='append', index=False)
        print(f"Sucesso! {len(df_db)} postos importados para a tabela 'postos'.")
    except Exception as e:
        print("\nERRO CRÍTICO NA IMPORTAÇÃO:")
        print(e)
     

if __name__ == "__main__":
    importar_postos()