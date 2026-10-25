import datetime
import io
import logging
import os
import re
import shutil
import time
import unicodedata
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import psycopg2
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from tqdm import tqdm


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def validar_identificador(valor: str) -> str:
    """
    Valida nomes de schemas, tabelas e índices SQL.

    Evita SQL injection em identificadores interpolados nas queries.
    """
    if not isinstance(valor, str) or not re.match(
        r"^[A-Za-z_][A-Za-z0-9_]*$",
        valor,
    ):
        raise ValueError(
            f"Identificador SQL inválido: {valor}. "
            "Use somente letras, números e underscore."
        )
    return valor


def normalizar_coluna(nome: str) -> str:
    """
    Remove acentos e padroniza nomes de colunas para comparação.
    """
    nome_normalizado = unicodedata.normalize(
        "NFKD",
        str(nome),
    )

    return "".join(
        caractere
        for caractere in nome_normalizado
        if not unicodedata.combining(caractere)
    ).upper().strip()


def tabela_ref(schema: str, tabela: str) -> str:
    """
    Retorna uma referência SQL segura e com aspas duplas.
    """
    schema = validar_identificador(schema)
    tabela = validar_identificador(tabela)

    return f'"{schema}"."{tabela}"'


def obter_parametros_psycopg2(db_uri: str) -> dict:
    """
    Extrai parâmetros de conexão da DATABASE_URL para psycopg2.
    """
    parsed_uri = urlparse(db_uri)

    return {
        "host": parsed_uri.hostname,
        "port": parsed_uri.port or 5432,
        "dbname": parsed_uri.path.lstrip("/"),
        "user": parsed_uri.username,
        "password": parsed_uri.password,
    }


# =============================================================================
# Estruturas do banco
# =============================================================================

def inicializar_estruturas_banco(
    engine,
    schema: str,
    hourly_table_name: str,
    stations_table_name: str,
    staging_schema: str,
):
    """
    Cria schemas, tabelas auxiliares, tabelas finais e índices necessários.
    """
    schema = validar_identificador(schema)
    staging_schema = validar_identificador(staging_schema)
    hourly_table_name = validar_identificador(hourly_table_name)
    stations_table_name = validar_identificador(stations_table_name)

    hourly_ref = tabela_ref(schema, hourly_table_name)
    stations_ref = tabela_ref(schema, stations_table_name)
    staging_ref = tabela_ref(
        staging_schema,
        "stg_dados_inmet_horarios",
    )

    logger.info("Inicializando estruturas do banco para o INMET...")

    queries = [
        f'CREATE SCHEMA IF NOT EXISTS "{schema}";',
        f'CREATE SCHEMA IF NOT EXISTS "{staging_schema}";',
        f"""
        CREATE TABLE IF NOT EXISTS {stations_ref} (
            "CODIGO" VARCHAR(20) PRIMARY KEY,
            "ESTACAO" VARCHAR(255),
            "LATITUDE" FLOAT,
            "LONGITUDE" FLOAT,
            "ALTITUDE" FLOAT,
            "DATA DE FUNDACAO" DATE
        );
        """,
        f"""
        CREATE TABLE IF NOT EXISTS {hourly_ref} (
            "DATA_HORA" TIMESTAMP NOT NULL,
            "CODIGO_ESTACAO" VARCHAR(20) NOT NULL,
            "PRECIPITACAO" FLOAT,
            "PRESSAO_ATM" FLOAT,
            "RADIACAO" FLOAT,
            "TEMP_AR" FLOAT,
            "TEMP_MAX" FLOAT,
            "TEMP_MIN" FLOAT,
            "UMID_MAX" FLOAT,
            "UMID_MIN" FLOAT,
            "UMID_AR" FLOAT,
            PRIMARY KEY ("DATA_HORA", "CODIGO_ESTACAO")
        );
        """,
        f"""
        CREATE UNLOGGED TABLE IF NOT EXISTS {staging_ref} (
            "PRECIPITACAO" TEXT,
            "PRESSAO_ATM" TEXT,
            "RADIACAO" TEXT,
            "TEMP_AR" TEXT,
            "TEMP_MAX" TEXT,
            "TEMP_MIN" TEXT,
            "UMID_MAX" TEXT,
            "UMID_MIN" TEXT,
            "UMID_AR" TEXT,
            "DATA_HORA" TEXT,
            "CODIGO_ESTACAO" TEXT
        );
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{hourly_table_name}_estacao_data"
        ON {hourly_ref} ("CODIGO_ESTACAO", "DATA_HORA");
        """,
        f"""
        CREATE INDEX IF NOT EXISTS
        "idx_{hourly_table_name}_data"
        ON {hourly_ref} ("DATA_HORA");
        """,
    ]

    with engine.begin() as conn:
        for query in queries:
            conn.execute(text(query))


def tabela_estacoes_possui_dados(
    engine,
    schema: str,
    stations_table_name: str,
) -> bool:
    """
    Retorna True somente se a tabela existir e possuir coordenadas válidas.
    """
    stations_ref = tabela_ref(schema, stations_table_name)

    query = text(f"""
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = :schema
              AND table_name = :table_name
        )
        AND EXISTS (
            SELECT 1
            FROM {stations_ref}
            WHERE "CODIGO" IS NOT NULL
              AND "LATITUDE" IS NOT NULL
              AND "LONGITUDE" IS NOT NULL
        );
    """)

    with engine.connect() as conn:
        resultado = conn.execute(
            query,
            {
                "schema": schema,
                "table_name": stations_table_name,
            },
        ).scalar()

    return bool(resultado)


# =============================================================================
# Download e extração
# =============================================================================

def baixar_e_extrair_ano(
    year: int,
    zip_dir: Path,
    raw_dir: Path,
) -> Path:
    """
    Baixa e extrai o ZIP anual do INMET, se necessário.

    Retorna o diretório que contém os CSVs extraídos.
    """
    zip_path = zip_dir / f"{year}.zip"
    year_dir = raw_dir / str(year)

    url = (
        "https://portal.inmet.gov.br/uploads/"
        f"dadoshistoricos/{year}.zip"
    )

    if not zip_path.exists():
        logger.info("Baixando arquivo do INMET: %s", url)

        response = requests.get(url, timeout=180)
        response.raise_for_status()

        with open(zip_path, "wb") as arquivo:
            arquivo.write(response.content)

    if not year_dir.exists():
        logger.info("Extraindo dados do INMET para %s...", year)

        with zipfile.ZipFile(zip_path, "r") as zip_file:
            zip_file.extractall(year_dir)

    return year_dir

# =============================================================================
# Metadados de estações
# =============================================================================

def extrair_metadados_estacoes(year_dir: Path) -> pd.DataFrame:
    """
    Extrai metadados das estações a partir dos cabeçalhos dos CSVs do INMET.
    """
    logger.info(
        "Extraindo metadados de estações de %s...",
        year_dir,
    )

    dataframes = []

    csv_files = (
        list(year_dir.rglob("*_SP_*.csv"))
        + list(year_dir.rglob("*_SP_*.CSV"))
    )

    for path in csv_files:
        metadata_lines = []

        for encoding in ["latin-1", "cp1252"]:
            try:
                with open(path, "r", encoding=encoding) as arquivo:
                    for _ in range(8):
                        linha = arquivo.readline().strip()

                        if ";" in linha:
                            metadata_lines.append(linha)

                break

            except UnicodeDecodeError:
                metadata_lines = []

        metadata = {}

        for linha in metadata_lines:
            if ";" not in linha:
                continue

            chave, valor = linha.split(";", 1)

            chave = normalizar_coluna(
                chave.replace(":", "")
            )

            metadata[chave] = valor.strip()

        if metadata:
            dataframes.append(pd.DataFrame([metadata]))

    if not dataframes:
        return pd.DataFrame()

    df_estacoes = pd.concat(
        dataframes,
        ignore_index=True,
    )

    possiveis_codigos = [
        "CODIGO (WMO)",
        "CODIGO_WMO",
        "CODIGO",
    ]

    coluna_codigo = next(
        (
            coluna
            for coluna in possiveis_codigos
            if coluna in df_estacoes.columns
        ),
        None,
    )

    if coluna_codigo is None:
        raise ValueError(
            "Não foi encontrada uma coluna de código WMO "
            "nos metadados do INMET."
        )

    df_estacoes = df_estacoes.rename(
        columns={coluna_codigo: "CODIGO"}
    )

    colunas_esperadas = [
        "ESTACAO",
        "CODIGO",
        "LATITUDE",
        "LONGITUDE",
        "ALTITUDE",
        "DATA DE FUNDACAO",
    ]

    for coluna in colunas_esperadas:
        if coluna not in df_estacoes.columns:
            df_estacoes[coluna] = None

    df_estacoes = df_estacoes[colunas_esperadas].copy()

    df_estacoes["CODIGO"] = (
        df_estacoes["CODIGO"]
        .astype(str)
        .str.strip()
    )

    for coluna in ["LATITUDE", "LONGITUDE", "ALTITUDE"]:
        df_estacoes[coluna] = pd.to_numeric(
            df_estacoes[coluna]
            .astype(str)
            .str.replace(",", ".", regex=False),
            errors="coerce",
        )

    df_estacoes["DATA DE FUNDACAO"] = pd.to_datetime(
        df_estacoes["DATA DE FUNDACAO"],
        dayfirst=True,
        errors="coerce",
    )

    df_estacoes = df_estacoes.dropna(
        subset=["CODIGO", "LATITUDE", "LONGITUDE"]
    )

    return df_estacoes.drop_duplicates(
        subset=["CODIGO"]
    ).reset_index(drop=True)


def carregar_estacoes(
    engine,
    schema: str,
    stations_table_name: str,
    year_dir: Optional[Path],
    load_stations: bool,
):
    """
    Atualiza ou reutiliza a tabela persistida de estações.

    Quando load_stations=False, exige uma tabela existente com coordenadas
    válidas e evita truncar os metadados persistidos.
    """
    stations_ref = tabela_ref(schema, stations_table_name)

    if not load_stations:
        if not tabela_estacoes_possui_dados(
            engine=engine,
            schema=schema,
            stations_table_name=stations_table_name,
        ):
            raise RuntimeError(
                f"A tabela de estações {stations_ref} não possui "
                "estações com código, latitude e longitude válidos. "
                "Execute uma vez com load_stations=True."
            )

        logger.info(
            "Utilizando tabela persistida de estações: %s",
            stations_ref,
        )
        return

    if year_dir is None:
        raise ValueError(
            "year_dir é obrigatório quando load_stations=True."
        )

    df_estacoes = extrair_metadados_estacoes(year_dir)

    if df_estacoes.empty:
        raise RuntimeError(
            "Não foi possível extrair metadados de estações do INMET."
        )

    logger.info(
        "Atualizando %s estações em %s...",
        f"{len(df_estacoes):,}",
        stations_ref,
    )

    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {stations_ref};"))

    df_estacoes.to_sql(
        name=stations_table_name,
        con=engine,
        schema=schema,
        if_exists="append",
        index=False,
        chunksize=1_000,
        method="multi",
    )

    logger.info(
        "Tabela de estações atualizada com %s registros.",
        f"{len(df_estacoes):,}",
    )


# =============================================================================
# Leitura e transformação dos CSVs horários
# =============================================================================

def encontrar_coluna(
    colunas: list,
    palavras_chave: list,
    excluir: Optional[list] = None,
) -> Optional[int]:
    """
    Localiza o índice da primeira coluna que contém as palavras-chave.
    """
    for indice, coluna in enumerate(colunas):
        coluna_normalizada = normalizar_coluna(coluna)

        if not all(
            palavra in coluna_normalizada
            for palavra in palavras_chave
        ):
            continue

        if excluir and any(
            palavra in coluna_normalizada
            for palavra in excluir
        ):
            continue

        return indice

    return None


def extrair_codigo_estacao_do_nome(path: Path) -> Optional[str]:
    """
    Obtém o código da estação a partir do nome padrão do arquivo INMET.

    Exemplo comum:
    INMET_SE_SP_A701_SAO PAULO_01-01-2024_A_31-12-2024.CSV
    """
    partes = path.name.split("_")

    if len(partes) >= 4:
        return partes[3].strip()

    return None


def ler_csv_horario_inmet(path: Path) -> pd.DataFrame:
    """
    Lê, normaliza e transforma um CSV de dados horários do INMET.
    """
    codigo_estacao = extrair_codigo_estacao_do_nome(path)

    if not codigo_estacao:
        return pd.DataFrame()

    dataframe = None

    for encoding in ["latin-1", "cp1252"]:
        try:
            dataframe = pd.read_csv(
                path,
                encoding=encoding,
                sep=";",
                skiprows=8,
            ).dropna(axis=1, how="all")

            break

        except UnicodeDecodeError:
            continue

        except pd.errors.EmptyDataError:
            return pd.DataFrame()

    if dataframe is None or dataframe.empty:
        return pd.DataFrame()

    colunas_originais = dataframe.columns.tolist()

    mapeamento = {
        "DATA_RAW": encontrar_coluna(
            colunas_originais,
            ["DATA"],
        ),
        "HORA_RAW": encontrar_coluna(
            colunas_originais,
            ["HORA"],
        ),
        "PRECIPITACAO": encontrar_coluna(
            colunas_originais,
            ["PRECIPIT"],
        ),
        "PRESSAO_ATM": encontrar_coluna(
            colunas_originais,
            ["PRESSAO", "NIVEL"],
            excluir=["MAX", "MIN"],
        ),
        "RADIACAO": encontrar_coluna(
            colunas_originais,
            ["RADIACAO"],
        ),
        "TEMP_AR": encontrar_coluna(
            colunas_originais,
            ["TEMPERATURA", "BULBO"],
        ),
        "TEMP_MAX": encontrar_coluna(
            colunas_originais,
            ["TEMPERATURA", "MAX"],
        ),
        "TEMP_MIN": encontrar_coluna(
            colunas_originais,
            ["TEMPERATURA", "MIN"],
        ),
        "UMID_MAX": encontrar_coluna(
            colunas_originais,
            ["UMIDADE", "MAX"],
        ),
        "UMID_MIN": encontrar_coluna(
            colunas_originais,
            ["UMIDADE", "MIN"],
        ),
        "UMID_AR": encontrar_coluna(
            colunas_originais,
            ["UMIDADE", "RELATIVA"],
            excluir=["MAX", "MIN"],
        ),
    }

    if (
        mapeamento["DATA_RAW"] is None
        or mapeamento["HORA_RAW"] is None
    ):
        return pd.DataFrame()

    mapeamento_valido = {
        coluna_destino: indice
        for coluna_destino, indice in mapeamento.items()
        if indice is not None
    }

    dataframe = dataframe.iloc[
        :,
        list(mapeamento_valido.values()),
    ].copy()

    dataframe.columns = list(mapeamento_valido.keys())

    for coluna in dataframe.columns:
        if coluna in ["DATA_RAW", "HORA_RAW"]:
            continue

        dataframe[coluna] = pd.to_numeric(
            dataframe[coluna]
            .astype(str)
            .str.replace(",", ".", regex=False),
            errors="coerce",
        )

        dataframe.loc[
            dataframe[coluna] <= -9999,
            coluna,
        ] = np.nan

    hora_limpa = (
        dataframe["HORA_RAW"]
        .astype(str)
        .str.replace(r"[:\sUTC]", "", regex=True)
        .str.zfill(4)
    )

    dataframe["DATA_HORA"] = pd.to_datetime(
        dataframe["DATA_RAW"].astype(str)
        + " "
        + hora_limpa,
        errors="coerce",
    )

    linhas_invalidas = dataframe["DATA_HORA"].isna()

    if linhas_invalidas.any():
        dataframe.loc[linhas_invalidas, "DATA_HORA"] = pd.to_datetime(
            dataframe.loc[linhas_invalidas, "DATA_RAW"].astype(str)
            + " "
            + hora_limpa.loc[linhas_invalidas],
            dayfirst=True,
            errors="coerce",
        )

    dataframe["CODIGO_ESTACAO"] = codigo_estacao

    return (
        dataframe
        .drop(columns=["DATA_RAW", "HORA_RAW"])
        .dropna(subset=["DATA_HORA"])
        .reset_index(drop=True)
    )


# =============================================================================
# Carga incremental no PostgreSQL
# =============================================================================

def carregar_dados_horarios_incremental(
    dataframe: pd.DataFrame,
    engine,
    db_uri: str,
    schema: str,
    hourly_table_name: str,
    staging_schema: str,
):
    """
    Carrega dados em staging usando COPY e executa UPSERT na tabela final.

    COPY é usado por desempenho e copy_expert permite referenciar corretamente
    tabelas com schema, como "stg"."stg_dados_inmet_horarios".
    """
    if dataframe.empty:
        logger.warning("Nenhum dado horário para carregar.")
        return

    hourly_ref = tabela_ref(schema, hourly_table_name)
    staging_ref = tabela_ref(
        staging_schema,
        "stg_dados_inmet_horarios",
    )

    colunas_ordem = [
        "PRECIPITACAO",
        "PRESSAO_ATM",
        "RADIACAO",
        "TEMP_AR",
        "TEMP_MAX",
        "TEMP_MIN",
        "UMID_MAX",
        "UMID_MIN",
        "UMID_AR",
        "DATA_HORA",
        "CODIGO_ESTACAO",
    ]

    dataframe = dataframe.copy()

    for coluna in colunas_ordem:
        if coluna not in dataframe.columns:
            dataframe[coluna] = np.nan

    dataframe = dataframe[colunas_ordem]

    dataframe = dataframe.replace(
        {
            np.nan: None,
            pd.NaT: None,
        }
    )

    buffer = io.StringIO()

    dataframe.to_csv(
        buffer,
        index=False,
        header=False,
        sep="\t",
        na_rep="\\N",
    )

    buffer.seek(0)

    colunas_sql = ", ".join(
        f'"{coluna}"'
        for coluna in colunas_ordem
    )

    copy_sql = f"""
        COPY {staging_ref} ({colunas_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            DELIMITER E'\\t',
            NULL '\\N'
        )
    """

    parametros_psycopg2 = obter_parametros_psycopg2(db_uri)

    conexao = psycopg2.connect(**parametros_psycopg2)

    try:
        with conexao.cursor() as cursor:
            cursor.execute(f"TRUNCATE TABLE {staging_ref};")
            cursor.copy_expert(copy_sql, buffer)

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

    colunas_update = [
        coluna
        for coluna in colunas_ordem
        if coluna not in ["DATA_HORA", "CODIGO_ESTACAO"]
    ]

    update_sql = ", ".join(
        f'"{coluna}" = EXCLUDED."{coluna}"'
        for coluna in colunas_update
    )

    colunas_insert_sql = ", ".join(
        f'"{coluna}"'
        for coluna in colunas_ordem
    )

    select_sql = """
        "PRECIPITACAO"::FLOAT,
        "PRESSAO_ATM"::FLOAT,
        "RADIACAO"::FLOAT,
        "TEMP_AR"::FLOAT,
        "TEMP_MAX"::FLOAT,
        "TEMP_MIN"::FLOAT,
        "UMID_MAX"::FLOAT,
        "UMID_MIN"::FLOAT,
        "UMID_AR"::FLOAT,
        "DATA_HORA"::TIMESTAMP,
        "CODIGO_ESTACAO"::VARCHAR
    """

    upsert_query = f"""
        INSERT INTO {hourly_ref} (
            {colunas_insert_sql}
        )
        SELECT
            {select_sql}
        FROM {staging_ref}
        ON CONFLICT ("DATA_HORA", "CODIGO_ESTACAO")
        DO UPDATE SET
            {update_sql};
    """

    with engine.begin() as conn:
        conn.execute(text(upsert_query))


# =============================================================================
# Pipeline principal INMET
# =============================================================================

def run_inmet_etl(
    db_uri: str,
    start_year: int,
    end_year: Optional[int] = None,
    delete_local: bool = False,
    schema: str = "modelos",
    hourly_table_name: str = "bz_inmet_horarios",
    stations_table_name: str = "bz_inmet_estacoes",
    staging_schema: str = "stg",
    load_stations: bool = False,
    stations_year: Optional[int] = None,
):
    """
    Executa o ETL do INMET.

    Parâmetros principais:
    - load_stations=False: mantém e reutiliza a tabela existente de estações.
    - load_stations=True: extrai metadados do ano definido em stations_year,
      trunca a tabela de estações e a recarrega.
    - dados horários são inseridos ou atualizados incrementalmente por
      ("DATA_HORA", "CODIGO_ESTACAO").
    """
    if not db_uri:
        raise ValueError("db_uri não foi informado.")

    if start_year is None:
        raise ValueError("start_year é obrigatório.")

    end_year = end_year or datetime.datetime.now().year
    stations_year = stations_year or end_year

    if start_year > end_year:
        raise ValueError(
            "start_year não pode ser maior que end_year."
        )

    if stations_year < start_year or stations_year > end_year:
        raise ValueError(
            "stations_year deve estar entre start_year e end_year."
        )

    schema = validar_identificador(schema)
    hourly_table_name = validar_identificador(hourly_table_name)
    stations_table_name = validar_identificador(stations_table_name)
    staging_schema = validar_identificador(staging_schema)

    inicio = time.time()

    base_dir = Path("./.temp_inmet")
    zip_dir = base_dir / "_zip"
    raw_dir = base_dir / "_raw"

    zip_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(db_uri)

    inicializar_estruturas_banco(
        engine=engine,
        schema=schema,
        hourly_table_name=hourly_table_name,
        stations_table_name=stations_table_name,
        staging_schema=staging_schema,
    )

    # Valida a tabela persistida antes de iniciar os downloads, se a carga
    # de estações estiver desabilitada.
    if not load_stations:
        carregar_estacoes(
            engine=engine,
            schema=schema,
            stations_table_name=stations_table_name,
            year_dir=None,
            load_stations=False,
        )

    for year in range(start_year, end_year + 1):
        try:
            logger.info("Processando dados INMET para o ano %s...", year)

            year_dir = baixar_e_extrair_ano(
                year=year,
                zip_dir=zip_dir,
                raw_dir=raw_dir,
            )

            if load_stations and year == stations_year:
                carregar_estacoes(
                    engine=engine,
                    schema=schema,
                    stations_table_name=stations_table_name,
                    year_dir=year_dir,
                    load_stations=True,
                )

            csv_files = (
                list(year_dir.rglob("*_SP_*.csv"))
                + list(year_dir.rglob("*_SP_*.CSV"))
            )

            if not csv_files:
                logger.warning(
                    "Nenhum CSV do estado de São Paulo encontrado para %s.",
                    year,
                )
                continue

            dataframes = []

            for file_path in tqdm(
                csv_files,
                desc=f"Lendo CSVs INMET {year}",
            ):
                df_arquivo = ler_csv_horario_inmet(file_path)

                if not df_arquivo.empty:
                    dataframes.append(df_arquivo)

            if not dataframes:
                logger.warning(
                    "Nenhum CSV climático válido encontrado para %s.",
                    year,
                )
                continue

            df_final = pd.concat(
                dataframes,
                ignore_index=True,
            )

            carregar_dados_horarios_incremental(
                dataframe=df_final,
                engine=engine,
                db_uri=db_uri,
                schema=schema,
                hourly_table_name=hourly_table_name,
                staging_schema=staging_schema,
            )

            logger.info(
                "INMET %s: %s registros carregados.",
                year,
                f"{len(df_final):,}",
            )

            if year_dir.exists():
                shutil.rmtree(year_dir)

        except Exception as erro:
            logger.error(
                "Erro ao processar INMET %s: %s",
                year,
                erro,
                exc_info=True,
            )

    if delete_local and base_dir.exists():
        shutil.rmtree(base_dir)

    logger.info(
        "ETL INMET finalizado em %.2f segundos.",
        time.time() - inicio,
    )


# =============================================================================
# Execução direta opcional
# =============================================================================

if __name__ == "__main__":
    load_dotenv(
        "/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example"
    )

    DB_URI = os.getenv("DATABASE_URL")

    if not DB_URI:
        raise ValueError(
            "A variável DATABASE_URL não foi encontrada."
        )

    run_inmet_etl(
        db_uri=DB_URI,
        start_year=2022,
        end_year=2026,
        delete_local=True,
        schema="modelos",
        hourly_table_name="bz_inmet_horarios",
        stations_table_name="bz_inmet_estacoes",
        staging_schema="stg",

        # Na primeira carga, defina como True.
        # Em execuções seguintes, mantenha False.
        load_stations=False,

        # Utilizado somente se load_stations=True.
        stations_year=2025,
    )