import os
import sys
import time

# Nome do arquivo do banco de dados (para apagar e recriar do zero)
# Verifique se no seu db.py o nome é este mesmo (ex: 'banco_dados.db' ou 'app.db')
ARQUIVO_DB = "sinan.db" 

def main():
    print("--- INICIANDO PROCESSO TOTAL ---\n")

    # 1. SEGURANÇA: Apagar o banco antigo para garantir que a nova estrutura (sem unique) seja criada
    if os.path.exists(ARQUIVO_DB):
        print(f"  Removendo banco de dados antigo ({ARQUIVO_DB}) para garantir estrutura limpa...")
        try:
            os.remove(ARQUIVO_DB)
            print("✅ Banco antigo removido.")
        except Exception as e:
            print(f"Não foi possível remover o arquivo (ele pode estar aberto): {e}")
    
    # Lista de scripts na ordem correta de dependência
    scripts = [
        "createdb.py",            # Cria as tabelas vazias (Lê models.py e db.py)
        "pipeline_municipios.py", # 1º Popula as Cidades (base para as FKs)
        "pipeline_acidentes.py",  # 2º Popula acidentes
        "pipeline_postos.py"      # 3º Popula postos
    ]

    for script in scripts:
        print(f"\n{'='*40}")
        print(f" RODANDO: {script}")
        print(f"{'='*40}")
        
        # Verifica se o arquivo existe antes de tentar rodar
        if not os.path.exists(script):
            print(f" ERRO: O arquivo '{script}' não foi encontrado nesta pasta.")
            print("   Verifique se o nome está correto (ex: pipeline_muncipios vs pipeline_municipios)")
            sys.exit(1)

        # Executa o script usando o interpretador Python atual
        codigo_erro = os.system(f'{sys.executable} {script}')
        
        if codigo_erro != 0:
            print(f"\nOcorreu um erro crítico no {script}. O processo foi interrompido.")
            sys.exit(1)
        else:
            print(f" {script} finalizado com sucesso.")
            time.sleep(1) # Pausa dramática de 1 seg

    print("\n PROCESSO CONCLUÍDO! TODOS OS DADOS IMPORTADOS. ")

if __name__ == "__main__":
    main()