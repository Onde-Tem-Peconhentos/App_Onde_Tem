import logging
import os

from dotenv import load_dotenv
from modelos_dados.sinan_etl_raw import run_sinan_etl
from modelos_dados.inmet_load_raw import run_inmet_etl, carregar_estacoes
from modelos_dados.inmet_transform_clean import atualizar_clima_mensal
from modelos_dados.inmet_interpolacao_cidades import atualizar_clima_municipal_interpolado


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


load_dotenv("/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example")
DB_URI = os.getenv("DATABASE_URL")

SCHEMA = "modelos"

TABELA_MUNICIPIOS = "municipios"
TABELA_SINAN = "bz_sinan_ocorrencias"

TABELA_INMET_HORARIA = "bz_inmet_horarios"
TABELA_INMET_ESTACOES = "bz_inmet_estacoes"

TABELA_INMET_MENSAL = "bz_inmet_clima_mensal"
TABELA_PESOS_IDW = "bz_pesos_idw_municipios_estacoes"
TABELA_CLIMA_MUNICIPAL_BASE = "bz_municipios_clima_base"
TABELA_CLIMA_MUNICIPAL_FINAL = "bz_municipios_clima_consolidado"

SCHEMA_STAGING = "stg"

K_ESTACOES = 4
IDW_POWER = 2

ATUALIZAR_ESTACOES_INMET = False 
RECALCULAR_PESOS_IDW = False
REPROCESSAR_CLIMA_COMPLETO = False

if __name__ == "__main__":
    if not DB_URI:
        raise ValueError(
            "A variável de ambiente DATABASE_URL não foi encontrada."
        )

    logger.info("Iniciando pipeline de dados e modelos...")
    logger.info("Iniciando ETL SINAN...")

    # run_sinan_etl(
    #     start_year=2022,
    #     local_dir=(
    #         "/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/"
    #         "pipelines/modelos_dados/dados_sinan"
    #     ),
    #     DB_URI=DB_URI,
    #     table_name=TABELA_SINAN,
    #     DIS_CODE="ANIM",
    #     schema=SCHEMA
    # )

    # run_inmet_etl(
    #     db_uri=DB_URI,
    #     start_year=2022,
    #     end_year=2026,
    #     delete_local=True,
    #     schema=SCHEMA,
    #     hourly_table_name=TABELA_INMET_HORARIA,
    #     stations_table_name=TABELA_INMET_ESTACOES,
    #     staging_schema=SCHEMA_STAGING,
    #     load_stations=ATUALIZAR_ESTACOES_INMET,
    #     stations_year=2025,
    # )

    # linhas_agregadas = atualizar_clima_mensal(
    #     db_uri=DB_URI,
    #     schema="modelos",
    #     tabela_horaria="bz_inmet_horarios",
    #     tabela_mensal="bz_inmet_clima_mensal",
    #     reprocessar_completo=False,
    #     data_inicio=None,
    # )

    atualizar_clima_municipal_interpolado(
    db_uri=DB_URI,
    schema="modelos",
    tabela_municipios="sz_municipios",
    tabela_estacoes="bz_inmet_estacoes",
    tabela_clima_mensal="bz_inmet_clima_mensal",
    tabela_pesos="bz_pesos_idw",
    tabela_saida="sz_municipios_clima_interpolado",
    coluna_id_municipio="codigo",
    coluna_lat_municipio="latitude",
    coluna_lon_municipio="longitude",
    coluna_id_estacao="CODIGO",
    coluna_lat_estacao="LATITUDE",
    coluna_lon_estacao="LONGITUDE",
    k_estacoes=4,
    idw_power=2.0,
    recalcular_pesos_idw=False,
    reprocessar_completo=False,
    data_inicio=None,
    )


    logger.info("Pipeline de dados concluído.")

 