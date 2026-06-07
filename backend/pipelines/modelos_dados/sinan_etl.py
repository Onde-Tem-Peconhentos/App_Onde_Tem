import io
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from pysus.online_data.SINAN import SINAN
import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuração de Logs
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') # placeholder
DB_URI = os.getenv("DATABASE_URL")

DIS_CODE = "ANIM"
TABLE    = "ocorrencias_consolidado"

COLUMNS = [
    "DT_NOTIFIC", "SEM_NOT", "NU_ANO", "SG_UF_NOT", "ID_MUNICIP",
    "ANT_DT_ACI", "ANT_UF", "ANT_MUNIC_", "TP_ACIDENT",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _copy_to_db(df: pd.DataFrame, table: str, raw_conn) -> None:
    """Carga rápida via COPY FROM STDIN (psycopg2 copy_expert) no schema public."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    cols = ", ".join(f'"{c}"' for c in df.columns)
    sql  = (
        f"COPY {table} ({cols}) "
        f"FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
    )

    cursor = raw_conn.cursor()
    try:
        cursor.copy_expert(sql, buffer)
        raw_conn.commit()
    except Exception:
        raw_conn.rollback()
        raise
    finally:
        cursor.close()


def _ensure_table(engine, df: pd.DataFrame, table: str) -> None:
    """(Re)cria a tabela no schema public com a estrutura do DataFrame."""
    with engine.connect() as conn:
        # Dropa tabela para garantir estrutura correta
        conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
        conn.commit()
        logger.info(f"Tabela '{table}' removida (se existia).")

    # Recria tabela com a estrutura exata do DataFrame no public
    df.head(0).to_sql(
        name=table,
        con=engine,
        if_exists="replace",
        index=False,
    )
    logger.info(f"Tabela '{table}' criada com {len(df.columns)} colunas.")


# ---------------------------------------------------------------------------
# ETL principal
# ---------------------------------------------------------------------------

def run_etl(start_year: int, end_year: int, local_dir: str) -> None:
    """Executa o pipeline ETL para dados do SINAN."""
    download_dir = Path(local_dir)
    download_dir.mkdir(parents=True, exist_ok=True)

    # 1. EXTRAÇÃO
    logger.info("Conectando ao SINAN e buscando lista de arquivos...")
    sinan = SINAN().load()
    files = sinan.get_files(dis_code=[DIS_CODE])

    if not files:
        logger.warning("Nenhum arquivo encontrado no SINAN.")
        return

    logger.info(f"Baixando {len(files)} arquivo(s) para '{download_dir}'...")
    sinan.download(files=files, local_dir=str(download_dir))

    # 2. TRANSFORMAÇÃO
    logger.info("Processando arquivos baixados...")
    dataframes = []

    for file_path in sorted(download_dir.glob("*.parquet")):
        try:
            df = pd.read_parquet(file_path)
            logger.info(f"  {file_path.name}: {len(df):,} linhas, {len(df.columns)} colunas")

            cols_to_keep = [c for c in COLUMNS if c in df.columns]
            if "ANT_MUNIC_" in df.columns:
                df = df[
                    df["ANT_MUNIC_"]
                    .astype(str)
                    .str.startswith("35", na=False)
                ]

            dataframes.append(df[cols_to_keep])

        except Exception as e:
            logger.error(f"Erro ao processar '{file_path.name}': {e}")

    if not dataframes:
        logger.error("Nenhum dado válido foi processado. Abortando.")
        return

    final_df = pd.concat(dataframes, ignore_index=True)
    
    mapping_animal = {
        1: "Serpente", 2: "Aranha", 3: "Escorpião", 
        4: "Lagarta", 5: "Abelha", 6: "Outros", 9: "Ignorado",
    }

    if "TP_ACIDENT" in final_df.columns:
        final_df["ANIMAL"] = (
            pd.to_numeric(final_df["TP_ACIDENT"], errors="coerce")
            .map(mapping_animal)
            .fillna("Desconhecido")
        )
        final_df.drop(columns=["TP_ACIDENT"], inplace=True)

    for date_col in ("ANT_DT_ACI", "DT_NOTIFIC"):
        if date_col in final_df.columns:
            final_df[date_col] = pd.to_datetime(final_df[date_col], errors="coerce")

    # 3. CARGA
    logger.info("Iniciando carga no PostgreSQL (schema public)...")
    engine = create_engine(DB_URI, pool_size=5, max_overflow=10)

    try:
        _ensure_table(engine, final_df, TABLE)

        raw_conn = engine.raw_connection()
        try:
            _copy_to_db(final_df, TABLE, raw_conn)
            logger.info(f"ETL finalizado! {len(final_df):,} linhas carregadas em 'public.{TABLE}'.")
            
            # Validação
            _validate_load(engine, final_df, TABLE)
        finally:
            raw_conn.close()

    except Exception as e:
        logger.error(f"Falha ao carregar dados no PostgreSQL: {e}", exc_info=True)


# ---------------------------------------------------------------------------
# Validação pós-carga
# ---------------------------------------------------------------------------

def _validate_load(engine, df_loaded: pd.DataFrame, table: str) -> None:
    """Verifica se a carga foi bem-sucedida no schema public."""
    logger.info("--- Validação pós-carga ---")
    with engine.connect() as conn:
        # 1. Contagem de linhas
        count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        expected = len(df_loaded)
        status = "✓ OK" if count == expected else "✗ DIVERGÊNCIA"
        logger.info(f"  Linhas esperadas : {expected:,}")
        logger.info(f"  Linhas no banco    : {count:,}  [{status}]")

        # 2. Amostra
        sample = conn.execute(text(f"SELECT * FROM {table} LIMIT 3"))
        rows = sample.fetchall()
        logger.info(f"  Amostra (3 linhas):")
        for row in rows:
            logger.info(f"    {dict(row._mapping)}")

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    run_etl(start_year=2007, end_year=2026, local_dir="./dados_sinan")