#script para testar o download de dados do SINAN usando a biblioteca PYSUS
import pandas as pd
from pysus.online_data.SINAN import SINAN

# --- CONFIGURAÇÃO DO TESTE ---
ANO = 2022
CODIGO_DOENCA = 'ANIM' 

print(f"--- Iniciando teste de download com PYSUS (fluxo final) ---")

try:
    # 1. Carrega os metadados do SINAN
    print("Conectando ao SINAN e carregando lista de arquivos...")
    sinan = SINAN().load()
    print("Lista de arquivos carregada.")

    # 2. Encontra a lista de objetos de arquivo
    print(f"Buscando arquivos para a doença '{CODIGO_DOENCA}' e ano '{ANO}'...")
    arquivos_encontrados = sinan.get_files(dis_code=CODIGO_DOENCA, year=ANO)

    if not arquivos_encontrados:
        raise FileNotFoundError(f"Nenhum arquivo encontrado para '{CODIGO_DOENCA}' no ano {ANO}.")

    # --- CORREÇÃO DO FLUXO AQUI ---

    # 3. Pegamos o primeiro objeto de arquivo da lista
    arquivo_para_baixar = arquivos_encontrados[0]
    print(f"Arquivo alvo encontrado: {arquivo_para_baixar.name}")

    # 4. Chamamos o download a partir do objeto de arquivo específico
    print("Iniciando o download...")
    # Isso retorna um objeto Parquet, não uma lista
    objeto_parquet = arquivo_para_baixar.download()
    print(f"\n✅ Download concluído! Arquivo salvo em: {objeto_parquet.path}")

    # 5. Usamos o método .to_dataframe() para ler o arquivo
    print("\nLendo o arquivo baixado...")
    df = objeto_parquet.to_dataframe()
    
    # --- FIM DA CORREÇÃO ---
    
    print("-" * 30)
    print(f"Total de {len(df)} registros encontrados para {ANO}.")
    print("\nAmostra dos dados baixados (5 primeiras linhas):")
    print(df.head())

except Exception as e:
    print(f"\n❌ ERRO: Ocorreu um problema: {e}")