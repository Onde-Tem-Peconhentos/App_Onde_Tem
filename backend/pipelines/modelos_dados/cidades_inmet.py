import pandas as pd
import numpy as np
import logging

from sqlalchemy import create_engine, text
from tqdm import tqdm
import os
from dotenv import load_dotenv


# =============================================================================
# Configuração
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') # placeholder
DB_URI = os.getenv("DATABASE_URL")

TABELA_SAIDA = "municipios_clima_consolidado"

K_ESTACOES = 5
IDW_POWER = 2


# =============================================================================
# Mapa de nomes curtos
# =============================================================================

CLIMA_SQL = {
    "TEMP_AR": "AVG",
    "PRECIPITACAO": "SUM",
    "UMID_AR": "AVG",
    "PRESSAO_ATM": "AVG",
    "RADIACAO": "SUM",
    "TEMP_MAX": "MAX",
    "TEMP_MIN": "MIN",
    "UMID_MAX": "MAX",
    "UMID_MIN": "MIN",
}

NOMES_CURTOS = {
    "TEMP_AR": "temp",
    "PRECIPITACAO": "prec",
    "UMID_AR": "umid",
    "PRESSAO_ATM": "press",
    "RADIACAO": "rad",
    "TEMP_MAX": "tmax",
    "TEMP_MIN": "tmin",
    "UMID_MAX": "umax",
    "UMID_MIN": "umin",
}

COLS_CLIMA = list(CLIMA_SQL.keys())


# =============================================================================
# Funções auxiliares
# =============================================================================

def haversine_matrix_km(lat1, lon1, lat2, lon2):
    """
    Matriz de distância Haversine em km.
    """
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))

    dlat = lat1[:, None] - lat2[None, :]
    dlon = lon1[:, None] - lon2[None, :]

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1[:, None])
        * np.cos(lat2[None, :])
        * np.sin(dlon / 2) ** 2
    )

    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))

    return 6371.0088 * c


def safe_numeric(df, cols):
    for col in cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# =============================================================================
# 1. Extração
# =============================================================================

def obter_dados_base(engine):
    logger.info("Extraindo dados base do PostgreSQL...")

    with engine.connect() as conn:
        df_mun = pd.read_sql(
            """
            SELECT 
                codigo,
                municipio,
                latitude,
                longitude
            FROM municipios
            """,
            conn
        )

        df_est = pd.read_sql(
            """
            SELECT 
                "CODIGO",
                "LATITUDE",
                "LONGITUDE"
            FROM dados_estacoes
            """,
            conn
        )

        query_clima = text("""
            SELECT 
                "CODIGO_ESTACAO",
                DATE_TRUNC('month', "DATA_HORA") AS dt_ref,
                EXTRACT(YEAR FROM "DATA_HORA")::int AS ano,
                EXTRACT(MONTH FROM "DATA_HORA")::int AS mes,

                AVG("TEMP_AR")      AS "TEMP_AR",
                SUM("PRECIPITACAO") AS "PRECIPITACAO",
                AVG("UMID_AR")      AS "UMID_AR",
                AVG("PRESSAO_ATM")  AS "PRESSAO_ATM",
                SUM("RADIACAO")     AS "RADIACAO",
                MAX("TEMP_MAX")     AS "TEMP_MAX",
                MIN("TEMP_MIN")     AS "TEMP_MIN",
                MAX("UMID_MAX")     AS "UMID_MAX",
                MIN("UMID_MIN")     AS "UMID_MIN"

            FROM dados_inmet_horarios
            GROUP BY 1, 2, 3, 4
        """)

        df_clima = pd.read_sql(query_clima, conn)

    df_mun = safe_numeric(df_mun, ["latitude", "longitude"])
    df_est = safe_numeric(df_est, ["LATITUDE", "LONGITUDE"])

    df_mun = df_mun.dropna(subset=["latitude", "longitude"]).copy()
    df_est = df_est.dropna(subset=["LATITUDE", "LONGITUDE"]).copy()

    df_clima["dt_ref"] = pd.to_datetime(df_clima["dt_ref"])

    logger.info(f"Municípios: {len(df_mun):,}")
    logger.info(f"Estações: {len(df_est):,}")
    logger.info(f"Linhas clima mensal estação: {len(df_clima):,}")

    return df_mun, df_est, df_clima


# =============================================================================
# 2. Interpolação IDW
# =============================================================================

def criar_pesos_idw(df_mun, df_est, k=5, power=2):
    logger.info(f"Criando pesos IDW com k={k}, power={power}...")

    lat_mun = df_mun["latitude"].values
    lon_mun = df_mun["longitude"].values

    lat_est = df_est["LATITUDE"].values
    lon_est = df_est["LONGITUDE"].values

    dist = haversine_matrix_km(lat_mun, lon_mun, lat_est, lon_est)

    registros = []

    for i, mun in enumerate(df_mun.itertuples(index=False)):
        idx = np.argsort(dist[i])[:k]

        d = dist[i, idx]
        d = np.where(d == 0, 1e-6, d)

        pesos = 1 / (d ** power)
        pesos = pesos / pesos.sum()

        for j, p, dist_km in zip(idx, pesos, d):
            registros.append({
                "codigo_municipio": mun.codigo,
                "nome_municipio": mun.municipio,
                "codigo_estacao": df_est.iloc[j]["CODIGO"],
                "dist_est_km": dist_km,
                "peso": p,
            })

    df_pesos = pd.DataFrame(registros)

    resumo = (
        df_pesos
        .groupby(["codigo_municipio", "nome_municipio"])
        .agg(
            dist_min_km=("dist_est_km", "min"),
            dist_med_km=("dist_est_km", "mean"),
            peso_max=("peso", "max"),
            n_est=("codigo_estacao", "nunique"),
        )
        .reset_index()
    )

    return df_pesos, resumo


def interpolar_clima_municipios(df_mun, df_est, df_clima, k=5, power=2):
    logger.info("Interpolando clima municipal por IDW...")

    df_pesos, df_resumo_pesos = criar_pesos_idw(
        df_mun=df_mun,
        df_est=df_est,
        k=k,
        power=power
    )

    df_clima = df_clima.rename(columns={"CODIGO_ESTACAO": "codigo_estacao"})

    df_join = df_clima.merge(
        df_pesos,
        on="codigo_estacao",
        how="inner"
    )

    for col in COLS_CLIMA:
        df_join[col] = pd.to_numeric(df_join[col], errors="coerce")
        df_join[f"{col}_w"] = df_join[col] * df_join["peso"]

    cols_w = [f"{c}_w" for c in COLS_CLIMA]

    df_ag = (
        df_join
        .groupby(
            [
                "codigo_municipio",
                "nome_municipio",
                "dt_ref",
                "ano",
                "mes"
            ],
            as_index=False
        )[cols_w]
        .sum()
    )

    rename_w = {
        f"{col}_w": NOMES_CURTOS[col]
        for col in COLS_CLIMA
    }

    df_ag = df_ag.rename(columns=rename_w)

    df_ag = df_ag.merge(
        df_resumo_pesos,
        on=["codigo_municipio", "nome_municipio"],
        how="left"
    )

    return df_ag


# =============================================================================
# 3. Feature engineering
# =============================================================================
def aplicar_feature_engineering(df):
    logger.info("Aplicando feature engineering...")

    df = df.copy()

    df["dt_ref"] = pd.to_datetime(df["dt_ref"])
    df["anomes"] = df["dt_ref"].dt.strftime("%Y%m").astype(int)
    df["ano"] = df["dt_ref"].dt.year.astype(int)
    df["mes"] = df["dt_ref"].dt.month.astype(int)

    df = df.sort_values(["codigo_municipio", "anomes"]).copy()

    clima_cols = [
        "temp",
        "prec",
        "umid",
        "press",
        "rad",
        "tmax",
        "tmin",
        "umax",
        "umin",
    ]

    novas_cols = {}

    # -------------------------------------------------------------------------
    # Variáveis derivadas simples
    # -------------------------------------------------------------------------

    novas_cols["tamp"] = df["tmax"] - df["tmin"]
    novas_cols["uamp"] = df["umax"] - df["umin"]

    novas_cols["temp_x_umid"] = df["temp"] * df["umid"]
    novas_cols["temp_x_prec"] = df["temp"] * df["prec"]
    novas_cols["prec_x_umid"] = df["prec"] * df["umid"]

    novas_cols["log_prec"] = np.log1p(df["prec"].clip(lower=0))
    novas_cols["log_rad"] = np.log1p(df["rad"].clip(lower=0))

    df_base = pd.concat([df, pd.DataFrame(novas_cols, index=df.index)], axis=1)

    base_cols = clima_cols + [
        "tamp",
        "uamp",
        "temp_x_umid",
        "temp_x_prec",
        "prec_x_umid",
        "log_prec",
        "log_rad",
    ]

    # -------------------------------------------------------------------------
    # Sazonalidade
    # -------------------------------------------------------------------------

    feat_sazonal = pd.DataFrame(index=df_base.index)

    feat_sazonal["mes_sin"] = np.sin(2 * np.pi * df_base["mes"] / 12)
    feat_sazonal["mes_cos"] = np.cos(2 * np.pi * df_base["mes"] / 12)

    # -------------------------------------------------------------------------
    # Anomalia espacial e z-score espacial no mês
    # -------------------------------------------------------------------------

    feat_espacial = {}

    for col in base_cols:
        media_mes = df_base.groupby("anomes")[col].transform("mean")
        std_mes = df_base.groupby("anomes")[col].transform("std")

        feat_espacial[f"{col}_ae"] = df_base[col] - media_mes
        feat_espacial[f"{col}_ze"] = (
            (df_base[col] - media_mes) / std_mes.replace(0, np.nan)
        )

    feat_espacial = pd.DataFrame(feat_espacial, index=df_base.index)

    # -------------------------------------------------------------------------
    # Anomalia contra climatologia mensal do município
    # -------------------------------------------------------------------------

    feat_clim = {}

    for col in base_cols:
        clim_mun_mes = (
            df_base
            .groupby(["codigo_municipio", "mes"])[col]
            .transform("mean")
        )

        feat_clim[f"{col}_ac"] = df_base[col] - clim_mun_mes

    feat_clim = pd.DataFrame(feat_clim, index=df_base.index)

    # -------------------------------------------------------------------------
    # Lags, médias móveis e diferenças
    # -------------------------------------------------------------------------

    feat_temporal = {}

    g = df_base.groupby("codigo_municipio", group_keys=False)

    for col in base_cols:
        lag1 = g[col].shift(1)
        lag2 = g[col].shift(2)
        lag3 = g[col].shift(3)

        m3 = g[col].transform(
            lambda s: s.rolling(3, min_periods=1).mean()
        )

        m6 = g[col].transform(
            lambda s: s.rolling(6, min_periods=1).mean()
        )

        m12 = g[col].transform(
            lambda s: s.rolling(12, min_periods=1).mean()
        )

        feat_temporal[f"{col}_l1"] = lag1
        feat_temporal[f"{col}_l2"] = lag2
        feat_temporal[f"{col}_l3"] = lag3
        feat_temporal[f"{col}_m3"] = m3
        feat_temporal[f"{col}_m6"] = m6
        feat_temporal[f"{col}_m12"] = m12
        feat_temporal[f"{col}_d1"] = df_base[col] - lag1
        feat_temporal[f"{col}_d3"] = df_base[col] - m3

    feat_temporal = pd.DataFrame(feat_temporal, index=df_base.index)

    # -------------------------------------------------------------------------
    # Concatenar tudo de uma vez
    # -------------------------------------------------------------------------

    df_out = pd.concat(
        [
            df_base,
            feat_sazonal,
            feat_espacial,
            feat_clim,
            feat_temporal,
        ],
        axis=1
    )

    df_out = df_out.replace([np.inf, -np.inf], np.nan)

    # De-fragmenta o DataFrame
    df_out = df_out.copy()

    cols_id = [
        "codigo_municipio",
        "nome_municipio",
        "dt_ref",
        "anomes",
        "ano",
        "mes",
    ]

    cols_geo_est = [
        "dist_min_km",
        "dist_med_km",
        "peso_max",
        "n_est",
    ]

    outras_cols = [
        c for c in df_out.columns
        if c not in cols_id + cols_geo_est
    ]

    df_out = df_out[cols_id + cols_geo_est + outras_cols]

    logger.info(
        f"Dataset final: {df_out.shape[0]:,} linhas x {df_out.shape[1]:,} colunas"
    )

    return df_out

# =============================================================================
# 4. Carga no banco
# =============================================================================

def carregar_no_banco(df, engine, tabela=TABELA_SAIDA):
    if df.empty:
        logger.warning("DataFrame vazio. Nada será carregado.")
        return

    logger.info(f"Carregando {len(df):,} linhas em '{tabela}'...")

    with engine.begin() as conn:
        conn.execute(text(f"DROP TABLE IF EXISTS {tabela}"))

    df.to_sql(
        tabela,
        engine,
        if_exists="replace",
        index=False,
        chunksize=5_000
    )

    with engine.begin() as conn:
        conn.execute(text(
            f'CREATE INDEX idx_{tabela}_mun_anomes '
            f'ON {tabela} ("codigo_municipio", "anomes")'
        ))

        conn.execute(text(
            f'CREATE INDEX idx_{tabela}_anomes '
            f'ON {tabela} ("anomes")'
        ))

    logger.info("Carga finalizada!")


# =============================================================================
# 5. Execução
# =============================================================================

if __name__ == "__main__":
    try:
        engine = create_engine(DB_URI)

        df_mun, df_est, df_clima = obter_dados_base(engine)

        df_final = interpolar_clima_municipios(
            df_mun=df_mun,
            df_est=df_est,
            df_clima=df_clima,
            k=K_ESTACOES,
            power=IDW_POWER
        )

        df_final = aplicar_feature_engineering(df_final)

        carregar_no_banco(
            df=df_final,
            engine=engine,
            tabela=TABELA_SAIDA
        )

        print(df_final.head())
        print(df_final.columns.tolist())

    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)