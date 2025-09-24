import pandas as pd


nome_do_arquivo = 'municipios_SP.csv'

print(f"--- ANÁLISE DO ARQUIVO '{nome_do_arquivo}' ---")
try:
    df = pd.read_csv(nome_do_arquivo, low_memory=False)
    print("\n✅ Arquivo lido com sucesso!")
    
    print("\nAmostra dos dados (5 primeiras linhas):")
    print(df.head())
    
    print("\n----------------------------------------------")
    
    print("\nInformações técnicas das colunas (Raio-X):")
    df.info()

except FileNotFoundError:
    print(f"❌ ERRO: Arquivo '{nome_do_arquivo}' não encontrado. Verifique o nome e se ele está na pasta correta.")
except Exception as e:
    print(f"❌ ERRO: {e}")