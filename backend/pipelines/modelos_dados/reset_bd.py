import logging
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ResetDB")

def reset_database():
    db_url = "postgresql://etl_user:etl_pass@localhost:5432/etl_db"
    engine = create_engine(db_url)
    
    tables = [
        "municipios_clima_consolidado",
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