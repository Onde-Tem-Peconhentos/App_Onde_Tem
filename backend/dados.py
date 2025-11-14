import pandas as pd
import io
import os

# Configuração dos nomes dos arquivos
arquivo_entrada = 'postos_atualizados.csv'
arquivo_saida_excel = 'postos_organizados.xlsx'
arquivo_saida_csv = 'postos_organizados.csv'

def organizar_dados():
    # Verifica se o arquivo de entrada existe
    if not os.path.exists(arquivo_entrada):
        print(f"Erro: O arquivo '{arquivo_entrada}' não foi encontrado na pasta.")
        return

    print("Lendo e processando o arquivo...")

    try:
        # 1. Ler as linhas do arquivo original
        # Usamos 'utf-8' ou 'latin-1' dependendo da codificação do seu arquivo. 
        # Se der erro de caracteres estranhos, tente mudar para encoding='latin-1'
        with open(arquivo_entrada, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 2. Limpeza linha por linha
        cleaned_lines = []
        for line in lines:
            s = line.strip() # Remove espaços e quebras de linha das pontas
            
            # O problema detectado era que a linha toda estava entre aspas, ex: "DADO1, DADO2"
            if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
                # Remove a aspa do começo e do fim
                content = s[1:-1]
                # Corrige aspas duplas que aparecem como "" no CSV (padrão de escape)
                content = content.replace('""', '"')
                cleaned_lines.append(content)
            else:
                # Caso a linha não esteja 'empacotada', apenas corrige aspas duplas internas
                cleaned_lines.append(s.replace('""', '"'))

        # Reconstrói o conteúdo CSV limpo
        csv_content = "\n".join(cleaned_lines)

        # 3. Carrega no Pandas para estruturar as colunas
        df = pd.read_csv(io.StringIO(csv_content))

        print(f"Dados processados com sucesso! Total de linhas: {len(df)}")

        # 4. Salva os arquivos novos
        # Excel
        print(f"Criando arquivo Excel: {arquivo_saida_excel}...")
        df.to_excel(arquivo_saida_excel, index=False)
        
        # CSV Limpo
        print(f"Criando arquivo CSV: {arquivo_saida_csv}...")
        df.to_csv(arquivo_saida_csv, index=False, encoding='utf-8-sig')

        print("\nProcesso concluído! Os arquivos foram salvos na mesma pasta.")
        print("\nVisualização das primeiras 5 linhas:")
        print(df.head())

    except Exception as e:
        print(f"\nOcorreu um erro durante o processamento: {e}")

if __name__ == "__main__":
    organizar_dados()