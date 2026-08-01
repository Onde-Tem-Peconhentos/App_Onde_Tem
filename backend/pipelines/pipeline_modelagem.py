from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import date
import logging
import numpy as np
import statsmodels.api as sm

from modelos_modelagem.ajuste_modelos import fit
from modelos_modelagem.geospatial import build_geojsons, build_geojson_forecast
from modelos_modelagem.persistencia import persist_results_mes

load_dotenv('/home/gabi/wkplace/ProjetoIC/App_Onde_Tem/backend/.env.example') # placeholder
DB_URI = os.getenv("DATABASE_URL")
engine = create_engine(
    DB_URI,
    pool_size=5,
    max_overflow=10,
)

end_date = date.today().strftime('%Y-%m-%d')
begin_date = pd.to_datetime("2022-01-01")

query_modelagem = """
WITH meses AS (
    SELECT generate_series(
        CAST(:begin_date AS date),
        CAST(:end_date AS date),
        INTERVAL '1 month'
    )::date AS dt
),

grid AS (
    SELECT
        m.codigo AS id_municipio,
        me.dt AS dt_referencia,
        TO_CHAR(me.dt, 'YYYYMM')::bigint AS anomes
    FROM modelos.municipios m
    CROSS JOIN meses me
),

ocorrencias AS (
    SELECT
        "ANT_MUNIC_"::bigint AS id_municipio,
        DATE_TRUNC('month', "ANT_DT_ACI")::date AS dt,
        COUNT(*) AS total_ocorrencias
    FROM modelos.ocorrencias_consolidado
    WHERE "ANIMAL" = :animal
    GROUP BY id_municipio, dt
)

SELECT
    g.id_municipio,
    g.anomes,
    g.dt_referencia,

    COALESCE(o.total_ocorrencias, 0) AS total_ocorrencias,

    -- =========================================================================
    -- Dados geográficos e socioeconômicos
    -- =========================================================================

    mu.latitude,
    mu.longitude,
    mu.populacao,

    mu."IDHM_RENDA2010",
    mu."IDHM_SAUDE2010",
    mu."IDHM_EDUCA2010",
    mu."IDHM_2010",

    mu."POP_RURAL",
    mu."POP_URBANA",

    mu."PIB2021",

    mu."N_FAVELAS",
    mu."POP_FAVELAS",

    mu."APARTAMENTO",
    mu."CASA",
    mu."VILA/CONDOMINIO",
    mu."TOTAL_MORADIA",

    mu."ALTITUDE",
    mu."SUPERFICE_VEGETAL2020",
    mu."VEGETACAO2020",
    mu."PERCENTUAL_VEGETACAO",
    mu."AREA_KM2",
    mu."PERCENTUAL_HOMENS",

    cl."temp",
    cl."prec",
    cl."umid",
    cl."press",
    cl."rad",
    cl."tmax",
    cl."tmin",
    cl."umax",
    cl."umin",

    cl."tamp",
    cl."uamp",
    cl."log_prec",
    cl."log_rad",

    cl."prec_l1",
    cl."prec_l2",
    cl."prec_l3",
    cl."prec_m3",
    cl."prec_m6",
    cl."prec_m12",
    cl."prec_d1",
    cl."prec_d3",
    cl."prec_ae",
    cl."prec_ze",
    cl."prec_ac",

    cl."log_prec_l1",
    cl."log_prec_l2",
    cl."log_prec_l3",
    cl."log_prec_m3",
    cl."log_prec_m6",
    cl."log_prec_m12",
    cl."log_prec_d1",
    cl."log_prec_d3",
    cl."log_prec_ae",
    cl."log_prec_ze",
    cl."log_prec_ac",

    cl."temp_l1",
    cl."temp_l2",
    cl."temp_l3",
    cl."temp_m3",
    cl."temp_m6",
    cl."temp_m12",
    cl."temp_d1",
    cl."temp_d3",
    cl."temp_ae",
    cl."temp_ze",
    cl."temp_ac",

    cl."tmax_m3",
    cl."tmax_m6",
    cl."tmax_ac",
    cl."tmax_ae",

    cl."tmin_m3",
    cl."tmin_m6",
    cl."tmin_ac",
    cl."tmin_ae",

    cl."tamp_l1",
    cl."tamp_l2",
    cl."tamp_l3",
    cl."tamp_m3",
    cl."tamp_m6",
    cl."tamp_m12",
    cl."tamp_d1",
    cl."tamp_d3",
    cl."tamp_ae",
    cl."tamp_ze",
    cl."tamp_ac",

    cl."umid_l1",
    cl."umid_l2",
    cl."umid_l3",
    cl."umid_m3",
    cl."umid_m6",
    cl."umid_m12",
    cl."umid_d1",
    cl."umid_d3",
    cl."umid_ae",
    cl."umid_ze",
    cl."umid_ac",

    cl."uamp_l1",
    cl."uamp_l2",
    cl."uamp_l3",
    cl."uamp_m3",
    cl."uamp_m6",
    cl."uamp_m12",
    cl."uamp_d1",
    cl."uamp_d3",
    cl."uamp_ae",
    cl."uamp_ze",
    cl."uamp_ac",

    cl."rad_l1",
    cl."rad_m3",
    cl."rad_m6",
    cl."rad_ae",
    cl."rad_ac",

    cl."log_rad_l1",
    cl."log_rad_m3",
    cl."log_rad_m6",
    cl."log_rad_ae",
    cl."log_rad_ac",

    cl."press_l1",
    cl."press_m3",
    cl."press_m6",
    cl."press_ae",
    cl."press_ac",

    cl."mes_sin",
    cl."mes_cos"

FROM grid g

LEFT JOIN ocorrencias o 
    ON g.id_municipio = o.id_municipio 
    AND g.dt_referencia = o.dt

LEFT JOIN modelos.municipios mu
    ON g.id_municipio = mu.codigo

LEFT JOIN modelos.municipios_clima_consolidado cl
    ON g.id_municipio = cl.codigo_municipio
    AND g.anomes = cl.anomes

ORDER BY 
    g.id_municipio, 
    g.dt_referencia
"""
query_plot = "select codigo, municipio, latitude, longitude, populacao, geometry from modelos.municipios"
query_animais = """SELECT DISTINCT "ANIMAL"
    FROM modelos.ocorrencias_consolidado
    WHERE "ANIMAL" NOT IN ('Ignorado', 'Outros')
    ORDER BY "ANIMAL"
"""

df_plot = pd.read_sql(text(query_plot), engine)
animais = pd.read_sql(text(query_animais), engine)["ANIMAL"].tolist()
print(animais)

forecast_month = 202605

for animal in animais:
    print(f"Processando: {animal}")

    df_modelos = pd.read_sql(text(query_modelagem), engine, params={
        "animal": animal, "begin_date": begin_date, "end_date": end_date,
    })

    result = resultado = fit(
        df_modelos,
        forecast_month=202606,
        inicio_teste=202601,
        fim_teste=202604,
        inicio_treino=202201,
        fim_treino=202512,
    )

    # GeoJSONs — teste
    ols_obs, ols_pred, ols_res = build_geojsons(
        df_plot, result["geo_ols_teste"], target="casos"
    )
    gwr_obs, gwr_pred, gwr_res = build_geojsons(
        df_plot, result["geo_gwr_teste"], target="casos"
    )

    # GeoJSONs — forecast
    ols_fc = build_geojson_forecast(df_plot, result["geo_ols_forecast"], target="casos")
    gwr_fc = build_geojson_forecast(df_plot, result["geo_gwr_forecast"], target="casos")

    persist_results_mes(
        engine=engine,
        animal=animal,
        result=result,
        geojsons={
            "ols_obs":      ols_obs,
            "ols_pred":     ols_pred,
            "ols_res":      ols_res,
            "ols_forecast": ols_fc,
            "gwr_obs":      gwr_obs,
            "gwr_pred":     gwr_pred,
            "gwr_res":      gwr_res,
            "gwr_forecast": gwr_fc,
        },
    )

    logging.info(
        f"[{animal}] Persistido — forecast={forecast_month}, "
        f"bw_gwr={result['meta']['gwr_bandwidth_km']:.2f} km, "
        f"features={len(result['meta']['selected_features'])}"
    )