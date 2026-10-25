import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResetDB")

load_dotenv("/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example")
db_url = os.getenv("DATABASE_URL")

def reset_database():
    engine = create_engine(db_url)
    
    tables = [
        "modelos.sz_municipios_clima_interpolado",
    ]
    
    logger.info("Starting database reset...")

    
    try:
        with engine.begin() as conn:
            for table in tables:
                # O CASCADE é fundamental para remover tabelas que possuem Foreign Keys
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
                logger.info(f"Dropped table: {table}")
        
        logger.info("Database reset successful. All INMET tables removed.")
        
    except Exception as e:
        logger.error(f"Failed to reset database: {e}")

if __name__ == "__main__":
    reset_database()