import pandas as pd
from sqlalchemy import create_engine, inspect

# --- CONFIGURAÇÃO ---
nome_banco_dados = 'sinan.db'

print(f"--- INSPECIONANDO O BANCO DE DADOS: {nome_banco_dados} ---")

try:
    # 1. Criar a conexão com o banco de dados
    engine = create_engine(f'sqlite:///{nome_banco_dados}')
    
    # 2. Inspecionar o banco para ver quais tabelas existem
    inspector = inspect(engine)
    nomes_das_tabelas = inspector.get_table_names()
    
    print(f"\n✅ Conexão bem-sucedida.")
    print(f"Tabelas encontradas no banco: {nomes_das_tabelas}")
    
    # 3. Se a tabela 'acidentes' existir, mostrar uma amostra
    if 'acidentes' in nomes_das_tabelas:
        print("\n--- Conteúdo da tabela 'acidentes' ---")
     # 3. Se a tabela 'acidentes' existir, mostrar uma amostra
   
        
        # Conecta e lê as 5 primeiras linhas da tabela 'acidentes'
        with engine.connect() as connection:
            df = pd.read_sql_table('acidentes', connection).head()
            print("Amostra dos dados (5 primeiras linhas):")
            print(df)
    else:
        print("\nA tabela 'acidentes' não foi encontrada no banco de dados.")
    if 'postos_saude' in nomes_das_tabelas:
        print("\n--- Conteúdo da tabela 'postos_saude' ---")
        with engine.connect() as connection:
            df_postos = pd.read_sql_table('postos_saude', connection).head()
            print("Amostra dos dados (5 primeiras linhas):")
            print(df_postos)

except Exception as e:
    print(f"\n❌ ERRO: Ocorreu um problema ao inspecionar o banco de dados: {e}")