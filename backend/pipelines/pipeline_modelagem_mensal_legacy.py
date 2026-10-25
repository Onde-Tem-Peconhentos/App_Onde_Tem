from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import date
import logging
import numpy as np
import statsmodels.api as sm

from modelos_modelagem.ajuste_modelos_mensal import fit_mensal
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
    )::date AS dt_referencia
),

grid AS (
    SELECT
        m.codigo::bigint AS id_municipio,
        me.dt_referencia,
        TO_CHAR(me.dt_referencia, 'YYYYMM')::bigint AS anomes
    FROM modelos.sz_municipios m
    CROSS JOIN meses me
),

ocorrencias AS (
    SELECT
        "ANT_MUNIC_"::bigint AS id_municipio,
        DATE_TRUNC('month', "ANT_DT_ACI")::date AS dt_referencia,
        COUNT(*)::bigint AS total_ocorrencias
    FROM modelos.bz_sinan_ocorrencias
    WHERE "ANIMAL" = :animal
    GROUP BY
        "ANT_MUNIC_"::bigint,
        DATE_TRUNC('month', "ANT_DT_ACI")::date
)

SELECT
    -- =========================================================================
    -- Identificação temporal e municipal
    -- =========================================================================

    g.id_municipio,
    g.anomes,
    g.dt_referencia,

    -- =========================================================================
    -- Variável-alvo
    -- =========================================================================

    COALESCE(o.total_ocorrencias, 0) AS total_ocorrencias,

    COALESCE(
        o.total_ocorrencias::double precision * 100000
        / NULLIF(mu.populacao, 0),
        0
    ) AS incidencia_100k,

    -- =========================================================================
    -- Dados geográficos e socioeconômicos municipais
    -- =========================================================================

    mu.latitude,
    mu.longitude,
    mu.populacao,

    mu."IDHM_RENDA2010",
    mu."IDHM_SAUDE2010",
    mu."IDHM_EDUCA2010",
    mu."IDHM_2010",

    mu."POP_RURAL" / mu.populacao AS perc_pop_rural,
    mu."POP_URBANA" / mu.populacao AS perc_pop_urbana,

    mu."PIB2021",

    mu."N_FAVELAS",
    mu."POP_FAVELAS",

    mu."APARTAMENTO" / mu."TOTAL_MORADIA" AS perc_apartamento,
    mu."CASA" / mu."TOTAL_MORADIA" AS perc_casa,
    mu."VILA/CONDOMINIO" / mu."TOTAL_MORADIA" AS perc_vila_condominio,
    mu."TOTAL_MORADIA" / mu.populacao AS perc_total_moradia,

    mu.populacao / mu."AREA_KM2" AS densidade_populacional,
    mu."ALTITUDE",
    mu."SUPERFICE_VEGETAL2020",
    mu."VEGETACAO2020",
    mu."PERCENTUAL_VEGETACAO",
    mu."AREA_KM2",
    mu."PERCENTUAL_HOMENS",

    -- =========================================================================
    -- Clima mensal interpolado
    -- Mantém aliases curtos para facilitar uso posterior no modelo.
    -- =========================================================================

    cl.temp_ar AS temp,
    cl.precipitacao_total AS prec,
    cl.umid_ar AS umid,
    cl.pressao_atm AS press,
    cl.radiacao AS rad,
    cl.temp_max AS tmax,
    cl.temp_min AS tmin,
    cl.umid_max AS umax,
    cl.umid_min AS umin,

    -- =========================================================================
    -- Indicadores mensais de precipitação
    -- =========================================================================

    cl.precipitacao_total,
    cl.precipitacao_media,
    cl.qtd_dias_chuva,
    cl.max_seq_dias_chuva,

    -- =========================================================================
    -- Indicadores mensais de temperatura
    -- =========================================================================

    cl.temp_ar,
    cl.temp_max,
    cl.temp_min,

    cl.amplitude_t_max,
    cl.amplitude_t_min,
    cl.amplitude_t_media,

    cl.qtd_dias_calor_intenso,
    cl.max_seq_dias_calor_intenso,

    -- =========================================================================
    -- Indicadores mensais de umidade
    -- =========================================================================

    cl.umid_ar,
    cl.umid_max,
    cl.umid_min,

    cl.amplitude_u_max,
    cl.amplitude_u_media,

    -- =========================================================================
    -- Pressão e radiação
    -- =========================================================================

    cl.pressao_atm,
    cl.radiacao,

   -- =========================================================================
    -- Tempo contínuo e sazonalidade
    -- =========================================================================

    (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS tempo_mes,

    SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS mes_sin,

    COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS mes_cos,

    -- =========================================================================
    -- Interações de variáveis climáticas com a tendência temporal
    -- =========================================================================

    cl.temp_ar * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS temp_x_tempo,

    cl.precipitacao_total * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS prec_x_tempo,

    cl.umid_ar * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS umid_x_tempo,

    cl.pressao_atm * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS press_x_tempo,

    cl.radiacao * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS rad_x_tempo,

    cl.temp_max * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS tmax_x_tempo,

    cl.temp_min * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS tmin_x_tempo,

    cl.umid_max * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS umax_x_tempo,

    cl.umid_min * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS umin_x_tempo,

    cl.amplitude_t_media * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS tamp_x_tempo,

    cl.amplitude_u_media * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS uamp_x_tempo,

    cl.qtd_dias_chuva * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS dias_chuva_x_tempo,

    cl.qtd_dias_calor_intenso * (
        EXTRACT(YEAR FROM g.dt_referencia)::integer * 12
        + EXTRACT(MONTH FROM g.dt_referencia)::integer
    ) AS dias_calor_x_tempo,

    -- =========================================================================
    -- Interações climáticas com o ciclo sazonal anual
    -- =========================================================================

    cl.temp_ar * SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS temp_x_mes_sin,

    cl.temp_ar * COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS temp_x_mes_cos,

    cl.precipitacao_total * SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS prec_x_mes_sin,

    cl.precipitacao_total * COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS prec_x_mes_cos,

    cl.umid_ar * SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS umid_x_mes_sin,

    cl.umid_ar * COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS umid_x_mes_cos,

    cl.qtd_dias_chuva * SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS dias_chuva_x_mes_sin,

    cl.qtd_dias_chuva * COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS dias_chuva_x_mes_cos,

    cl.qtd_dias_calor_intenso * SIN(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS dias_calor_x_mes_sin,

    cl.qtd_dias_calor_intenso * COS(
        2 * PI() * EXTRACT(MONTH FROM g.dt_referencia) / 12.0
    ) AS dias_calor_x_mes_cos

FROM grid g

LEFT JOIN ocorrencias o
    ON g.id_municipio = o.id_municipio
    AND g.dt_referencia = o.dt_referencia

LEFT JOIN modelos.sz_municipios mu
    ON g.id_municipio = mu.codigo::bigint

LEFT JOIN modelos.sz_municipios_clima_interpolado cl
    ON g.id_municipio::text = cl.codigo_municipio
    AND g.dt_referencia = cl.dt_ref

ORDER BY
    g.id_municipio,
    g.dt_referencia;
"""

query_mensal = """
WITH meses AS (
    SELECT generate_series(
        DATE_TRUNC('month', CAST(:begin_date AS date)),
        DATE_TRUNC('month', CAST(:end_date AS date)),
        INTERVAL '1 month'
    )::date AS dt_referencia
),

grid_mensal AS (
    SELECT
        m.codigo::bigint AS id_municipio,
        me.dt_referencia
    FROM modelos.sz_municipios m
    CROSS JOIN meses me
),

ocorrencias_mensais AS (
    SELECT
        "ANT_MUNIC_"::bigint AS id_municipio,
        DATE_TRUNC('month', "ANT_DT_ACI")::date AS dt_referencia,
        COUNT(*)::bigint AS total_ocorrencias
    FROM modelos.bz_sinan_ocorrencias
    WHERE "ANIMAL" = :animal
    GROUP BY
        "ANT_MUNIC_"::bigint,
        DATE_TRUNC('month', "ANT_DT_ACI")::date
),

-- ============================================================================
-- Base mensal completa
-- ============================================================================

base_mensal AS (
    SELECT
        g.id_municipio,
        g.dt_referencia,

        COALESCE(o.total_ocorrencias, 0) AS total_ocorrencias,

        mu.populacao,

        -- Dados municipais
        mu.latitude,
        mu.longitude,

        mu."IDHM_RENDA2010",
        mu."IDHM_SAUDE2010",
        mu."IDHM_EDUCA2010",
        mu."IDHM_2010",

        mu."POP_RURAL"::double precision
            / NULLIF(mu.populacao, 0) AS perc_pop_rural,

        mu."POP_URBANA"::double precision
            / NULLIF(mu.populacao, 0) AS perc_pop_urbana,

        mu."PIB2021",

        mu."N_FAVELAS",
        mu."POP_FAVELAS",

        mu."APARTAMENTO"::double precision
            / NULLIF(mu."TOTAL_MORADIA", 0) AS perc_apartamento,

        mu."CASA"::double precision
            / NULLIF(mu."TOTAL_MORADIA", 0) AS perc_casa,

        mu."VILA/CONDOMINIO"::double precision
            / NULLIF(mu."TOTAL_MORADIA", 0) AS perc_vila_condominio,

        mu."TOTAL_MORADIA"::double precision
            / NULLIF(mu.populacao, 0) AS perc_total_moradia,

        mu.populacao::double precision
            / NULLIF(mu."AREA_KM2", 0) AS densidade_populacional,

        mu."ALTITUDE",
        mu."SUPERFICE_VEGETAL2020",
        mu."VEGETACAO2020",
        mu."PERCENTUAL_VEGETACAO",
        mu."AREA_KM2",
        mu."PERCENTUAL_HOMENS",

        -- Clima
        cl.precipitacao_total,
        cl.precipitacao_media,
        cl.qtd_dias_chuva,
        cl.max_seq_dias_chuva,

        cl.temp_ar,
        cl.temp_max,
        cl.temp_min,

        cl.amplitude_t_max,
        cl.amplitude_t_min,
        cl.amplitude_t_media,

        cl.qtd_dias_calor_intenso,
        cl.max_seq_dias_calor_intenso,

        cl.umid_ar,
        cl.umid_max,
        cl.umid_min,

        cl.amplitude_u_max,
        cl.amplitude_u_media,

        cl.pressao_atm,
        cl.radiacao

    FROM grid_mensal g

    LEFT JOIN ocorrencias_mensais o
        ON g.id_municipio = o.id_municipio
        AND g.dt_referencia = o.dt_referencia

    LEFT JOIN modelos.sz_municipios mu
        ON g.id_municipio = mu.codigo::bigint

    LEFT JOIN modelos.sz_municipios_clima_interpolado cl
        ON g.id_municipio::text = cl.codigo_municipio
        AND g.dt_referencia = cl.dt_ref
),

-- ============================================================================
-- Identificação do trimestre antes da agregação
-- ============================================================================

base_mensal_trimestre AS (
    SELECT
        *,

        EXTRACT(YEAR FROM dt_referencia)::integer AS ano,

        EXTRACT(QUARTER FROM dt_referencia)::integer AS trimestre,

        DATE_TRUNC('quarter', dt_referencia)::date AS dt_trimestre

    FROM base_mensal
),

-- ============================================================================
-- Agregação município × trimestre
-- ============================================================================

base_trimestral AS (
    SELECT
        id_municipio,
        ano,
        trimestre,
        dt_trimestre::date AS dt_referencia,

        -- ====================================================================
        -- Variável-alvo
        -- ====================================================================

        SUM(total_ocorrencias)::bigint AS total_ocorrencias,

        SUM(total_ocorrencias)::double precision * 100000
            / NULLIF(MAX(populacao), 0) AS incidencia_100k,

        -- ====================================================================
        -- Dados municipais
        -- ====================================================================

        MAX(latitude) AS latitude,
        MAX(longitude) AS longitude,
        MAX(populacao) AS populacao,

        MAX("IDHM_RENDA2010") AS "IDHM_RENDA2010",
        MAX("IDHM_SAUDE2010") AS "IDHM_SAUDE2010",
        MAX("IDHM_EDUCA2010") AS "IDHM_EDUCA2010",
        MAX("IDHM_2010") AS "IDHM_2010",

        MAX(perc_pop_rural) AS perc_pop_rural,
        MAX(perc_pop_urbana) AS perc_pop_urbana,

        MAX("PIB2021") AS "PIB2021",

        MAX("N_FAVELAS") AS "N_FAVELAS",
        MAX("POP_FAVELAS") AS "POP_FAVELAS",

        MAX(perc_apartamento) AS perc_apartamento,
        MAX(perc_casa) AS perc_casa,
        MAX(perc_vila_condominio) AS perc_vila_condominio,
        MAX(perc_total_moradia) AS perc_total_moradia,

        MAX(densidade_populacional) AS densidade_populacional,

        MAX("ALTITUDE") AS "ALTITUDE",
        MAX("SUPERFICE_VEGETAL2020") AS "SUPERFICE_VEGETAL2020",
        MAX("VEGETACAO2020") AS "VEGETACAO2020",
        MAX("PERCENTUAL_VEGETACAO") AS "PERCENTUAL_VEGETACAO",
        MAX("AREA_KM2") AS "AREA_KM2",
        MAX("PERCENTUAL_HOMENS") AS "PERCENTUAL_HOMENS",

        -- ====================================================================
        -- Precipitação
        -- ====================================================================

        SUM(precipitacao_total) AS precipitacao_total,
        AVG(precipitacao_media) AS precipitacao_media,

        SUM(qtd_dias_chuva) AS qtd_dias_chuva,
        MAX(max_seq_dias_chuva) AS max_seq_dias_chuva,

        -- ====================================================================
        -- Temperatura
        -- ====================================================================

        AVG(temp_ar) AS temp_ar,
        MAX(temp_max) AS temp_max,
        MIN(temp_min) AS temp_min,

        AVG(amplitude_t_max) AS amplitude_t_max,
        AVG(amplitude_t_min) AS amplitude_t_min,
        AVG(amplitude_t_media) AS amplitude_t_media,

        SUM(qtd_dias_calor_intenso) AS qtd_dias_calor_intenso,
        MAX(max_seq_dias_calor_intenso) AS max_seq_dias_calor_intenso,

        -- ====================================================================
        -- Umidade
        -- ====================================================================

        AVG(umid_ar) AS umid_ar,
        MAX(umid_max) AS umid_max,
        MIN(umid_min) AS umid_min,

        AVG(amplitude_u_max) AS amplitude_u_max,
        AVG(amplitude_u_media) AS amplitude_u_media,

        -- ====================================================================
        -- Pressão / radiação
        -- ====================================================================

        AVG(pressao_atm) AS pressao_atm,
        AVG(radiacao) AS radiacao

    FROM base_mensal_trimestre

    GROUP BY
        id_municipio,
        ano,
        trimestre,
        dt_trimestre
),


-- ============================================================================
-- Feature book para prever incidência em t+1
-- Tudo abaixo usa apenas informação disponível até o fim do trimestre t.
-- ============================================================================

historico AS (
    SELECT
        *,
        DENSE_RANK() OVER (ORDER BY dt_referencia) AS t,

        -- Alvos em t+1
        LEAD(incidencia_100k, 1) OVER w AS target_incidencia_100k_t1,
        LEAD(total_ocorrencias, 1) OVER w AS target_ocorrencias_t1,

        -- Nível atual e histórico da incidência
        incidencia_100k AS incidencia_t,
        LAG(incidencia_100k, 1) OVER w AS incidencia_lag1,
        LAG(incidencia_100k, 2) OVER w AS incidencia_lag2,
        LAG(incidencia_100k, 3) OVER w AS incidencia_lag3,
        LAG(incidencia_100k, 4) OVER w AS incidencia_lag4,

        -- Médias móveis / dispersão da incidência, incluindo t
        AVG(incidencia_100k) OVER w2 AS incidencia_ma2,
        AVG(incidencia_100k) OVER w4 AS incidencia_ma4,
        STDDEV_SAMP(incidencia_100k) OVER w4 AS incidencia_sd4,
        MIN(incidencia_100k) OVER w4 AS incidencia_min4,
        MAX(incidencia_100k) OVER w4 AS incidencia_max4,

        -- Clima recente: t-1 e mesmo trimestre do ano anterior
        LAG(temp_ar, 1) OVER w AS temp_lag1,
        LAG(precipitacao_total, 1) OVER w AS prec_lag1,
        LAG(umid_ar, 1) OVER w AS umid_lag1,
        LAG(pressao_atm, 1) OVER w AS press_lag1,
        LAG(radiacao, 1) OVER w AS rad_lag1,
        LAG(qtd_dias_chuva, 1) OVER w AS dias_chuva_lag1,
        LAG(qtd_dias_calor_intenso, 1) OVER w AS dias_calor_lag1,

        LAG(temp_ar, 4) OVER w AS temp_lag4,
        LAG(precipitacao_total, 4) OVER w AS prec_lag4,
        LAG(umid_ar, 4) OVER w AS umid_lag4,
        LAG(radiacao, 4) OVER w AS rad_lag4,
        LAG(qtd_dias_chuva, 4) OVER w AS dias_chuva_lag4,
        LAG(qtd_dias_calor_intenso, 4) OVER w AS dias_calor_lag4,

        -- Resumos climáticos dos últimos 2 e 4 trimestres
        AVG(temp_ar) OVER w2 AS temp_ma2,
        AVG(temp_ar) OVER w4 AS temp_ma4,
        SUM(precipitacao_total) OVER w2 AS prec_sum2,
        SUM(precipitacao_total) OVER w4 AS prec_sum4,
        AVG(umid_ar) OVER w2 AS umid_ma2,
        AVG(umid_ar) OVER w4 AS umid_ma4,
        AVG(radiacao) OVER w2 AS rad_ma2,
        AVG(radiacao) OVER w4 AS rad_ma4,
        SUM(qtd_dias_chuva) OVER w4 AS dias_chuva_sum4,
        SUM(qtd_dias_calor_intenso) OVER w4 AS dias_calor_sum4,

        -- Extremos recentes
        MAX(temp_max) OVER w4 AS temp_max4,
        MIN(temp_min) OVER w4 AS temp_min4,
        MAX(max_seq_dias_chuva) OVER w4 AS seq_chuva_max4,
        MAX(max_seq_dias_calor_intenso) OVER w4 AS seq_calor_max4

    FROM base_trimestral
    WINDOW
        w  AS (PARTITION BY id_municipio ORDER BY dt_referencia),
        w2 AS (PARTITION BY id_municipio ORDER BY dt_referencia ROWS BETWEEN 1 PRECEDING AND CURRENT ROW),
        w4 AS (PARTITION BY id_municipio ORDER BY dt_referencia ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
),

features AS (
    SELECT
        *,

        -- Transformações da incidência
        LN(1 + incidencia_t) AS log_incidencia_t,
        incidencia_t - incidencia_lag1 AS incidencia_delta1,
        incidencia_t - incidencia_lag4 AS incidencia_delta4,
        (incidencia_t - incidencia_lag3) / 3.0 AS incidencia_tendencia4,
        incidencia_t - incidencia_ma4 AS incidencia_desvio_ma4,
        incidencia_sd4 / NULLIF(ABS(incidencia_ma4), 0) AS incidencia_cv4,
        LN((1 + incidencia_t) / NULLIF(1 + incidencia_lag1, 0)) AS incidencia_logratio1,
        LN((1 + incidencia_t) / NULLIF(1 + incidencia_lag4, 0)) AS incidencia_logratio4,

        -- Mudança climática recente e anual
        temp_ar - temp_lag1 AS temp_delta1,
        temp_ar - temp_lag4 AS temp_delta4,
        precipitacao_total - prec_lag1 AS prec_delta1,
        precipitacao_total - prec_lag4 AS prec_delta4,
        umid_ar - umid_lag1 AS umid_delta1,
        umid_ar - umid_lag4 AS umid_delta4,
        radiacao - rad_lag1 AS rad_delta1,
        qtd_dias_calor_intenso - dias_calor_lag1 AS dias_calor_delta1,
        qtd_dias_chuva - dias_chuva_lag1 AS dias_chuva_delta1,

        -- Posição do trimestre no ciclo anual
        SIN(2 * PI() * (trimestre - 1) / 4.0) AS trimestre_sin,
        COS(2 * PI() * (trimestre - 1) / 4.0) AS trimestre_cos

    FROM historico
)

SELECT *
FROM features
ORDER BY
    id_municipio,
    ano,
    trimestre;
"""
query_plot = "select codigo, municipio, latitude, longitude, populacao, geometry from modelos.sz_municipios"
query_animais = """SELECT DISTINCT "ANIMAL"
    FROM modelos.bz_sinan_ocorrencias
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

    result = resultado = fit_mensal(
        df_modelos,
        forecast_month=202606,
        inicio_teste=202601,
        fim_teste=202604,
        inicio_treino=202201,
        fim_treino=202512,
        target='incidencia_100k',
        drop_columns=['total_ocorrencias']
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