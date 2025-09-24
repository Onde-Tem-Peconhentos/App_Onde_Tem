from fastapi import FastAPI
from sqlalchemy import create_engine
import pandas as pd

# --- CONFIGURAÇÃO ---
# Nome do arquivo do banco de dados
nome_banco_dados = 'sinan.db'

# Criar a "conexão" com o banco de dados usando SQLAlchemy
engine = create_engine(f'sqlite:///{nome_banco_dados}')

app = FastAPI()
@app.get("/")
def read_root():
    """Endpoint raiz para verificar se a API está funcionando."""
    return {"status": "API da plataforma de acidentes online"}


@app.get("/api/acidentes")
def get_acidentes():
    """
    Lê a tabela 'acidentes' do banco de dados e retorna os 100 primeiros registros.
    """
    try:
        with engine.connect() as connection:
            # Cria uma consulta SQL para pedir ao banco APENAS 100 registros
            query = "SELECT * FROM acidentes LIMIT 100"
            
            # pd.read_sql_query para executa a consulta
            df = pd.read_sql_query(query, connection)
            
            resultados = df.to_dict(orient='records')
            return resultados
            
    except Exception as e:
        return {"erro": f"Não foi possível ler a tabela 'acidentes': {e}"}


    
@app.get("/api/postos_saude")
def get_postos_saude():
    """Lê a tabela 'postos_saude' e retorna os 100 primeiros registros."""
    try:
        with engine.connect() as connection:
            query = "SELECT * FROM postos_saude LIMIT 100"
            df = pd.read_sql_query(query, connection)
            return df.to_dict(orient='records')
    except Exception as e:
        return {"erro": f"Não foi possível ler a tabela 'postos_saude': {e}"}
    
    
    
@app.get("/api/municipios")
def get_municipios():
    """Lê a tabela 'municipios' e retorna os 100 primeiros registros."""
    try:
        with engine.connect() as connection:
            df = pd.read_sql_table('municipios', connection).head(100)
            return df.to_dict(orient='records')
    except Exception as e:
        return {"erro": f"Não foi possível ler a tabela 'municipios': {e}"}