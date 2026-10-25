from sqlalchemy import create_engine
from dotenv import load_dotenv
import pandas as pd
import os
from sqlalchemy import create_engine, text
from datetime import date
import logging
import numpy as np
import statsmodels.api as sm

# Pipeline unificado (mês/trimestre/semestre/ano) — ver
# modelos_modelagem/ajuste_modelos_unificado.py para o racional. A versão
# mensal dedicada (fit_mensal) continua intacta e utilizável isoladamente;
# uma cópia deste pipeline no formato anterior (somente mês) foi preservada
# em pipeline_modelagem_mensal_legacy.py.
from modelos_modelagem.ajuste_modelos_unificado import fit_periodo, haversine_matrix
from modelos_modelagem.geospatial import build_geojsons, build_geojson_forecast
from modelos_modelagem.persistencia import persist_results_periodo

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

    mu."IDHM_RENDA2010" AS idhm_renda,
    mu."IDHM_SAUDE2010" AS idhm_saude,
    mu."IDHM_EDUCA2010" AS idhm_educa,
    mu."IDHM_2010" AS idhm,

    mu."POP_RURAL" / mu.populacao AS perc_pop_rural,
    mu."POP_URBANA" / mu.populacao AS perc_pop_urbana,

    mu."PIB2021" AS pib,

    mu."N_FAVELAS" AS n_favelas,
    mu."POP_FAVELAS" AS pop_favelas,

    mu."APARTAMENTO" / mu."TOTAL_MORADIA" AS perc_apartamento,
    mu."CASA" / mu."TOTAL_MORADIA" AS perc_casa,
    mu."VILA/CONDOMINIO" / mu."TOTAL_MORADIA" AS perc_vila_condominio,
    mu."TOTAL_MORADIA" / mu.populacao AS perc_total_moradia,

    mu.populacao / mu."AREA_KM2" AS dens_pop,
    mu."ALTITUDE" AS altitude,
    mu."SUPERFICE_VEGETAL2020" AS area_vegetal,
    mu."VEGETACAO2020" AS veg_tipo,
    mu."PERCENTUAL_VEGETACAO" AS perc_veg,
    mu."AREA_KM2" AS area_km2,
    mu."PERCENTUAL_HOMENS" AS perc_homens,

    -- =========================================================================
    -- Clima mensal interpolado — um nome canônico curto por variável (sem
    -- aliases duplicados: antes a mesma coluna aparecia 2x, uma vez como
    -- alias curto e outra com o nome longo da tabela de origem).
    -- =========================================================================

    cl.temp_ar AS temp,
    cl.precipitacao_total AS prec,
    cl.precipitacao_media AS prec_med,
    cl.umid_ar AS umid,
    cl.pressao_atm AS press,
    cl.radiacao AS rad,
    cl.temp_max AS tmax,
    cl.temp_min AS tmin,
    cl.umid_max AS umax,
    cl.umid_min AS umin,

    cl.qtd_dias_chuva AS dias_chuva,
    cl.max_seq_dias_chuva AS seq_chuva,

    cl.amplitude_t_max AS amp_tmax,
    cl.amplitude_t_min AS amp_tmin,
    cl.amplitude_t_media AS amp_t,

    cl.qtd_dias_calor_intenso AS dias_calor,
    cl.max_seq_dias_calor_intenso AS seq_calor,

    cl.amplitude_u_max AS amp_umax,
    cl.amplitude_u_media AS amp_u

    -- Interações clima × tempo/sazonalidade calculadas aqui em mês bruto
    -- foram REMOVIDAS: nenhuma sobrevivia ao aggregate_period (nem em
    -- "mes" — confirmado: o whitelist de colunas da agregação nunca as
    -- incluía), então eram 23 colunas mortas, nunca vistas por nenhum
    -- modelo. Substituídas por `_add_interacoes_sazonais` em
    -- ajuste_modelos_unificado.py, que recalcula o equivalente (clima ×
    -- periodo_sin/periodo_cos) DEPOIS da agregação — funciona pra
    -- qualquer periodicidade, não só mês.

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

# Limita quais animais processar nesta execução. Edite esta lista (ou volte
# a `animais` completo) conforme necessário — mantido como variável separada
# para não perder a lista completa retornada pela query acima.
animais_para_processar = animais

# ---------------------------------------------------------------------------
# Features geográficas derivadas: distância até a capital (São Paulo) e até
# o litoral. Calculadas uma vez a partir de `df_plot` (coordenadas estáticas
# por município, via `haversine_matrix` já usado pelo núcleo de modelagem) e
# mescladas em cada `df_modelos` lido dentro do loop abaixo. Precisam estar
# em `_STATIC_COLS` (ajuste_modelos_unificado.py) pra sobreviver à agregação
# por periodicidade — já adicionadas lá.
# ---------------------------------------------------------------------------
LITORAL_MUNICIPIOS_SP = {
    "BERTIOGA", "CANANEIA", "CARAGUATATUBA", "CUBATAO", "GUARUJA", "IGUAPE",
    "ILHA COMPRIDA", "ILHABELA", "ITANHAEM", "MONGAGUA", "PERUIBE",
    "PRAIA GRANDE", "SANTOS", "SAO SEBASTIAO", "SAO VICENTE", "UBATUBA",
}


def _build_distancia_features(df_municipios):
    mu = df_municipios[["codigo", "municipio", "latitude", "longitude"]].copy()
    mu["municipio_norm"] = mu["municipio"].str.upper().str.strip()

    capital = mu.loc[mu["municipio_norm"] == "SAO PAULO"]
    if capital.empty:
        raise ValueError("Município SAO PAULO não encontrado em modelos.sz_municipios.")
    capital_coord = capital[["longitude", "latitude"]].to_numpy()

    litoral = mu.loc[mu["municipio_norm"].isin(LITORAL_MUNICIPIOS_SP)]
    faltando = LITORAL_MUNICIPIOS_SP - set(litoral["municipio_norm"])
    if faltando:
        print(f"[!] Municípios litorâneos não encontrados em sz_municipios: {sorted(faltando)}")
    litoral_coords = litoral[["longitude", "latitude"]].to_numpy()

    coords = mu[["longitude", "latitude"]].to_numpy()
    mu["dist_capital_km"] = haversine_matrix(coords, capital_coord)[:, 0]
    mu["dist_litoral_km"] = haversine_matrix(coords, litoral_coords).min(axis=1)

    return mu[["codigo", "dist_capital_km", "dist_litoral_km"]]


df_distancias = _build_distancia_features(df_plot)

# Configuração por periodicidade: períodos de treino/teste/forecast e janela
# rolling (em unidades do próprio período — meses, trimestres, semestres ou
# anos). Os valores de "mes" são os mesmos já usados antes da unificação.
# Os das demais periodicidades foram dimensionados para o histórico
# disponível (2022–2026): poucos anos completos, então "ano" em particular
# roda com uma janela rolling mínima e deve ser tratado como exploratório.
CADENCE_CONFIG = {
    "mes": dict(
        inicio_treino=202201, fim_treino=202512,
        inicio_teste=202601, fim_teste=202604,
        forecast_period=202606,
        rolling_window_periods=6, rolling_min_train_periods=3,
    ),
    "trimestre": dict(
        inicio_treino=20221, fim_treino=20244,
        inicio_teste=20251, fim_teste=20254,
        forecast_period=20262,
        rolling_window_periods=4, rolling_min_train_periods=2,
    ),
    "semestre": dict(
        inicio_treino=20221, fim_treino=20242,
        inicio_teste=20251, fim_teste=20252,
        forecast_period=20262,
        rolling_window_periods=3, rolling_min_train_periods=2,
    ),
    "ano": dict(
        inicio_treino=2022, fim_treino=2023,
        inicio_teste=2024, fim_teste=2025,
        forecast_period=2026,
        rolling_window_periods=1, rolling_min_train_periods=1,
    ),
}

# Cadências efetivamente rodadas nesta execução — as 4 completas. Edite
# este recorte conforme necessário pra rodar só um subconjunto.
CADENCES_ATIVAS = dict(CADENCE_CONFIG)

for animal in animais_para_processar:
    df_modelos = pd.read_sql(text(query_modelagem), engine, params={
        "animal": animal, "begin_date": begin_date, "end_date": end_date,
    })
    df_modelos = df_modelos.merge(df_distancias, left_on="id_municipio", right_on="codigo", how="left")
    df_modelos = df_modelos.drop(columns=["codigo"])

    for tipo_periodo, cfg in CADENCES_ATIVAS.items():
        print(f"Processando: {animal} [{tipo_periodo}]")

        result = fit_periodo(
            df_modelos,
            tipo_periodo=tipo_periodo,
            target='incidencia_100k',
            drop_columns=['total_ocorrencias'],
            **cfg,
        )

        # GeoJSONs — teste
        ols_obs, ols_pred, ols_res = build_geojsons(df_plot, result["geo_ols_teste"], target="casos")
        gwr_obs, gwr_pred, gwr_res = build_geojsons(df_plot, result["geo_gwr_teste"], target="casos")
        gwra_obs, gwra_pred, gwra_res = build_geojsons(df_plot, result["geo_gwra_teste"], target="casos")
        gtwr_obs, gtwr_pred, gtwr_res = build_geojsons(df_plot, result["geo_gtwr_teste"], target="casos")

        # GeoJSONs — forecast
        ols_fc = build_geojson_forecast(df_plot, result["geo_ols_forecast"], target="casos")
        gwr_fc = build_geojson_forecast(df_plot, result["geo_gwr_forecast"], target="casos")
        gwra_fc = build_geojson_forecast(df_plot, result["geo_gwra_forecast"], target="casos")
        gtwr_fc = build_geojson_forecast(df_plot, result["geo_gtwr_forecast"], target="casos")

        persist_results_periodo(
            engine=engine,
            animal=animal,
            tipo_periodo=tipo_periodo,
            result=result,
            geojsons={
                "ols_obs":       ols_obs,      "ols_pred":  ols_pred,  "ols_res":  ols_res,  "ols_forecast":  ols_fc,
                "gwr_obs":       gwr_obs,      "gwr_pred":  gwr_pred,  "gwr_res":  gwr_res,  "gwr_forecast":  gwr_fc,
                "gwra_obs":      gwra_obs,     "gwra_pred": gwra_pred, "gwra_res": gwra_res, "gwra_forecast": gwra_fc,
                "gtwr_obs":      gtwr_obs,     "gtwr_pred": gtwr_pred, "gtwr_res": gtwr_res, "gtwr_forecast": gtwr_fc,
            },
        )

        logging.info(
            f"[{animal}/{tipo_periodo}] Persistido — forecast={cfg['forecast_period']}, "
            f"bw_gwr={result['meta']['gwr_bandwidth_km']:.2f} km, "
            f"features={len(result['meta']['selected_features'])}"
        )