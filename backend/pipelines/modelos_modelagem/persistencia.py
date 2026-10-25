import json
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import text

# Rótulo exibido/persistido para cada periodicidade suportada pelo pipeline
# unificado (ajuste_modelos_unificado.fit_periodo). "Mês" é o mesmo rótulo já
# usado por persist_results_mes, para manter compatibilidade com os dados já
# persistidos e com o que o frontend hoje consulta.
TIPO_PERIODO_LABELS = {
    "mes": "Mês",
    "trimestre": "Trimestre",
    "semestre": "Semestre",
    "ano": "Ano",
}


def persist_results_mes(engine, animal: str, result: dict, geojsons: dict):
    # 1. DDL Enxuto (Sem lasso_alpha e sem loocv_mse)
    ddl = """
    CREATE SCHEMA IF NOT EXISTS modelos;

    CREATE TABLE IF NOT EXISTS modelos.bz_previsao (
        id                      SERIAL PRIMARY KEY,
        animal                  TEXT        NOT NULL,
        metodo                  TEXT        NOT NULL,
        data_processamento      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        tipo_periodo            TEXT        NOT NULL,
        train_month_inicio      INTEGER     NOT NULL,
        train_month_fim         INTEGER     NOT NULL,
        test_month_inicio       INTEGER     NOT NULL,
        test_month_fim          INTEGER     NOT NULL,
        test_last_month         INTEGER     NOT NULL,
        forecast_month          INTEGER     NOT NULL,
        n_train                 INTEGER     NOT NULL,
        n_test                  INTEGER     NOT NULL,
        selected_features       TEXT[]      NOT NULL,
        mse                     DOUBLE PRECISION,
        rmse                    DOUBLE PRECISION,
        mae                     DOUBLE PRECISION,
        r2                      DOUBLE PRECISION,
        gain_vs_media_municipal DOUBLE PRECISION,
        gwr_bandwidth_km        DOUBLE PRECISION,
        gwr_bandwidth_k         INTEGER,           
        gtwr_bandwidth_s        INTEGER,           
        gtwr_tau                DOUBLE PRECISION,  
        moran_i_medio           DOUBLE PRECISION,
        moran_p_sim_medio       DOUBLE PRECISION,
        moran_meses_signif      INTEGER,
        geojson_observado       TEXT,
        geojson_predito         TEXT,
        geojson_residuo         TEXT,
        geojson_forecast        TEXT,
        UNIQUE (animal, metodo, forecast_month, data_processamento)
    );
    """

    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()
        
    meta         = result["meta"]
    df_eval      = result["metricas"]
    arts         = result.get("artifacts", {})
    moran_resumo = result.get("moran_resumo", pd.DataFrame())

    def _get_metrics(metodo_label: str) -> dict:
        row = df_eval.loc[df_eval["modelo"].str.contains(metodo_label, case=False, regex=False)]
        if row.empty: 
            return {"mse": None, "rmse": None, "mae": None, "r2": None, "gain": None}
        row = row.iloc[0]
        return {
            "mse":  float(row["MSE"]) if not pd.isna(row["MSE"]) else None,
            "rmse": float(row["RMSE"]) if not pd.isna(row["RMSE"]) else None,
            "mae":  float(row["MAE"]) if not pd.isna(row["MAE"]) else None,
            "r2":   float(row["R2"]) if not pd.isna(row["R2"]) else None,
            "gain": float(row["gain_vs_media_municipal"]) if not pd.isna(row["gain_vs_media_municipal"]) else None,
        }

    def _get_moran(metodo_label: str) -> dict:
        if moran_resumo.empty: 
            return {"moran_i_medio": None, "moran_p_sim_medio": None, "moran_meses_signif": None}
            
        row = moran_resumo.loc[moran_resumo["modelo"].str.upper() == metodo_label.upper()]
        if row.empty: 
            return {"moran_i_medio": None, "moran_p_sim_medio": None, "moran_meses_signif": None}
            
        row = row.iloc[0]
        return {
            "moran_i_medio":      float(row["moran_I_medio"]) if not pd.isna(row["moran_I_medio"]) else None,
            "moran_p_sim_medio":  float(row["p_sim_medio"])   if not pd.isna(row["p_sim_medio"])   else None,
            "moran_meses_signif": int(row["meses_signif"])    if not pd.isna(row["meses_signif"])  else None,
        }

    def _to_float(x): return None if (x is None or pd.isna(x)) else float(x)
    def _to_int(x): return None if (x is None or pd.isna(x)) else int(float(x))

    now = datetime.now(timezone.utc)

    # 2. Definição das linhas que serão inseridas
    base_row = {
        "gwr_bandwidth_km": None, "gwr_bandwidth_k": None, 
        "gtwr_bandwidth_s": None, "gtwr_tau": None
    }

    rows = [
        # OLS Global
        {
            **base_row,
            "metodo":            "ols",
            "geojson_observado": geojsons.get("ols_obs"),
            "geojson_predito":   geojsons.get("ols_pred"),
            "geojson_residuo":   geojsons.get("ols_res"),
            "geojson_forecast":  geojsons.get("ols_forecast"),
            **_get_metrics("OLS Global"),
            **_get_moran("OLS")
        },
        # GWR Tradicional
        {
            **base_row,
            "metodo":            "gwr",
            "gwr_bandwidth_km":  _to_float(meta.get("gwr_bandwidth_km")),
            "geojson_observado": geojsons.get("gwr_obs"),
            "geojson_predito":   geojsons.get("gwr_pred"),
            "geojson_residuo":   geojsons.get("gwr_res"),
            "geojson_forecast":  geojsons.get("gwr_forecast"),
            **_get_metrics("GWR (Gaussiano)"),
            **_get_moran("GWR")
        },
        # GWR Adaptativo
        {
            **base_row,
            "metodo":            "gwr_adaptativo",
            "gwr_bandwidth_k":   _to_int(arts.get("gwra_bandwidth_k")),
            "geojson_observado": geojsons.get("gwra_obs"),
            "geojson_predito":   geojsons.get("gwra_pred"),
            "geojson_residuo":   geojsons.get("gwra_res"),
            "geojson_forecast":  geojsons.get("gwra_forecast"),
            **_get_metrics("GWR-Adaptativo"),
            **_get_moran("GWR_ADAPTATIVO")
        },
        # GTWR Gaussiano
        {
            **base_row,
            "metodo":            "gtwr",
            "gtwr_bandwidth_s":  _to_int(arts.get("gtwr_bandwidth_s")),
            "gtwr_tau":          _to_float(arts.get("gtwr_tau")),
            "geojson_observado": geojsons.get("gtwr_obs"),
            "geojson_predito":   geojsons.get("gtwr_pred"),
            "geojson_residuo":   geojsons.get("gtwr_res"),
            "geojson_forecast":  geojsons.get("gtwr_forecast"),
            **_get_metrics("GTWR - Gaussiano"),
            **_get_moran("GTWR")
        }
    ]

    # 3. String SQL de inserção
    stmt = text("""
        INSERT INTO modelos.bz_previsao (
            animal, metodo, tipo_periodo, data_processamento,
            train_month_inicio, train_month_fim, 
            test_month_inicio, test_month_fim,
            test_last_month, forecast_month, 
            n_train, n_test, selected_features,
            mse, rmse, mae, r2, gain_vs_media_municipal,
            gwr_bandwidth_km, gwr_bandwidth_k, 
            gtwr_bandwidth_s, gtwr_tau,
            moran_i_medio, moran_p_sim_medio, moran_meses_signif, 
            geojson_observado, geojson_predito, 
            geojson_residuo, geojson_forecast
        ) VALUES (
            :animal, :metodo, :tipo_periodo, :data_processamento,
            :tmi, :tmf, :temi, :temf, 
            :tlm, :fm, :ntr, :nte, :sf,
            :mse, :rmse, :mae, :r2, :gain,
            :gbwkm, :gbwk, :gtbw, :gttau,
            :mi, :mp, :ms,
            :gobs, :gpred, :gres, :gfc
        ) 
        ON CONFLICT (animal, metodo, forecast_month, data_processamento) 
        DO NOTHING
    """)

    # 4. Execução
    with engine.begin() as conn:
        for r in rows:
            conn.execute(stmt, {
                "animal":             animal, 
                "metodo":             r["metodo"], 
                "tipo_periodo":       "Mês", 
                "data_processamento": now,
                "tmi":                int(min(meta["train_months"])), 
                "tmf":                int(max(meta["train_months"])),
                "temi":               int(min(meta["test_months"])), 
                "temf":               int(max(meta["test_months"])),
                "tlm":                int(meta["test_last_month"]), 
                "fm":                 int(meta["forecast_month"]),
                "ntr":                int(meta["n_train"]), 
                "nte":                int(meta["n_test"]),
                "sf":                 list(meta["selected_features"]),
                "mse":                r["mse"], 
                "rmse":               r["rmse"], 
                "mae":                r["mae"], 
                "r2":                 r["r2"], 
                "gain":               r["gain"],
                "gbwkm":              r["gwr_bandwidth_km"], 
                "gbwk":               r["gwr_bandwidth_k"],
                "gtbw":               r["gtwr_bandwidth_s"], 
                "gttau":              r["gtwr_tau"],
                "mi":                 r["moran_i_medio"], 
                "mp":                 r["moran_p_sim_medio"], 
                "ms":                 r["moran_meses_signif"],
                "gobs":               r["geojson_observado"], 
                "gpred":              r["geojson_predito"], 
                "gres":               r["geojson_residuo"],
                "gfc":                r["geojson_forecast"]
            })


def persist_results_periodo(engine, animal: str, tipo_periodo: str, result: dict, geojsons: dict):
    """
    Equivalente a `persist_results_mes`, mas para o pipeline unificado
    (ajuste_modelos_unificado.fit_periodo), que serve qualquer periodicidade
    em vez de apenas mês. `persist_results_mes` é mantida intacta (mesma
    tabela, mesmo DDL) — esta função generaliza a leitura do `meta` (que usa
    as chaves genéricas train_periods/test_periods/... em vez de
    train_months/test_months/...), usa `tipo_periodo` em vez de fixar "Mês",
    e (2026) grava uma linha por método em `result["modelos_detalhados"]" —
    isso inclui as 3 baselines (zero, persistência, média municipal), antes
    nunca persistidas, e uma coluna `coeficientes` (JSONB) com o peso de
    cada variável: um valor único por variável no OLS, e quartis
    (q1/mediana/q3) entre municípios/observações nos modelos locais (GWR,
    GWR-Adaptativo, GTWR), já que seus coeficientes variam no espaço (e, no
    GTWR, também no tempo).
    """
    if tipo_periodo not in TIPO_PERIODO_LABELS:
        raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")

    ddl = """
    CREATE SCHEMA IF NOT EXISTS modelos;

    CREATE TABLE IF NOT EXISTS modelos.bz_previsao (
        id                      SERIAL PRIMARY KEY,
        animal                  TEXT        NOT NULL,
        metodo                  TEXT        NOT NULL,
        data_processamento      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        tipo_periodo            TEXT        NOT NULL,
        train_month_inicio      INTEGER     NOT NULL,
        train_month_fim         INTEGER     NOT NULL,
        test_month_inicio       INTEGER     NOT NULL,
        test_month_fim          INTEGER     NOT NULL,
        test_last_month         INTEGER     NOT NULL,
        forecast_month          INTEGER     NOT NULL,
        n_train                 INTEGER     NOT NULL,
        n_test                  INTEGER     NOT NULL,
        selected_features       TEXT[]      NOT NULL,
        mse                     DOUBLE PRECISION,
        rmse                    DOUBLE PRECISION,
        mae                     DOUBLE PRECISION,
        r2                      DOUBLE PRECISION,
        gain_vs_media_municipal DOUBLE PRECISION,
        gwr_bandwidth_km        DOUBLE PRECISION,
        gwr_bandwidth_k         INTEGER,
        gtwr_bandwidth_s        INTEGER,
        gtwr_tau                DOUBLE PRECISION,
        moran_i_medio           DOUBLE PRECISION,
        moran_p_sim_medio       DOUBLE PRECISION,
        moran_meses_signif      INTEGER,
        geojson_observado       TEXT,
        geojson_predito         TEXT,
        geojson_residuo         TEXT,
        geojson_forecast        TEXT,
        UNIQUE (animal, metodo, forecast_month, data_processamento)
    );

    -- Peso das variáveis por método: valor único (OLS) ou quartis entre
    -- municípios/observações (modelos locais). NULL para baselines e para
    -- linhas gravadas antes desta coluna existir.
    ALTER TABLE modelos.bz_previsao ADD COLUMN IF NOT EXISTS coeficientes JSONB;

    -- Estabilidade de cada variável do modelo final: em quantas das janelas
    -- rolling de seleção ela foi escolhida. Mesma para os 4 métodos "reais"
    -- de uma mesma execução (a seleção de variáveis acontece uma vez só,
    -- antes de ajustar cada modelo) — NULL para baselines.
    ALTER TABLE modelos.bz_previsao ADD COLUMN IF NOT EXISTS estabilidade_variaveis JSONB;
    """

    with engine.connect() as conn:
        conn.execute(text(ddl))
        conn.commit()

    meta              = result["meta"]
    moran_resumo      = result.get("moran_resumo", pd.DataFrame())
    modelos_detalhados = result["modelos_detalhados"]

    def _get_moran(metodo_key: str) -> dict:
        nulo = {"moran_i_medio": None, "moran_p_sim_medio": None, "moran_meses_signif": None}
        if moran_resumo.empty:
            return nulo
        # moran_resumo usa rótulos em maiúsculas (OLS, GWR, GWR_ADAPTATIVO, GTWR);
        # baselines não têm resíduos espaciais calculados, então não têm linha aqui.
        row = moran_resumo.loc[moran_resumo["modelo"].str.upper() == metodo_key.upper()]
        if row.empty:
            return nulo
        row = row.iloc[0]
        return {
            "moran_i_medio":      float(row["moran_I_medio"]) if not pd.isna(row["moran_I_medio"]) else None,
            "moran_p_sim_medio":  float(row["p_sim_medio"])   if not pd.isna(row["p_sim_medio"])   else None,
            "moran_meses_signif": int(row["meses_signif"])    if not pd.isna(row["meses_signif"])  else None,
        }

    # Geojsons só existem para os 4 métodos "reais" (baselines não geram mapa).
    GEOJSON_PREFIX = {"ols": "ols", "gwr": "gwr", "gwr_adaptativo": "gwra", "gtwr": "gtwr"}
    MORAN_LABEL = {"ols": "OLS", "gwr": "GWR", "gwr_adaptativo": "GWR_ADAPTATIVO", "gtwr": "GTWR"}

    now = datetime.now(timezone.utc)

    stmt = text("""
        INSERT INTO modelos.bz_previsao (
            animal, metodo, tipo_periodo, data_processamento,
            train_month_inicio, train_month_fim,
            test_month_inicio, test_month_fim,
            test_last_month, forecast_month,
            n_train, n_test, selected_features,
            mse, rmse, mae, r2, gain_vs_media_municipal,
            gwr_bandwidth_km, gwr_bandwidth_k,
            gtwr_bandwidth_s, gtwr_tau,
            coeficientes, estabilidade_variaveis,
            moran_i_medio, moran_p_sim_medio, moran_meses_signif,
            geojson_observado, geojson_predito,
            geojson_residuo, geojson_forecast
        ) VALUES (
            :animal, :metodo, :tipo_periodo, :data_processamento,
            :tmi, :tmf, :temi, :temf,
            :tlm, :fm, :ntr, :nte, :sf,
            :mse, :rmse, :mae, :r2, :gain,
            :gbwkm, :gbwk, :gtbw, :gttau,
            :coef, :estab,
            :mi, :mp, :ms,
            :gobs, :gpred, :gres, :gfc
        )
        ON CONFLICT (animal, metodo, forecast_month, data_processamento)
        DO NOTHING
    """)

    with engine.begin() as conn:
        for entry in modelos_detalhados:
            metodo_key = entry["metodo"]
            prefixo_geo = GEOJSON_PREFIX.get(metodo_key)
            moran = _get_moran(MORAN_LABEL[metodo_key]) if metodo_key in MORAN_LABEL else {
                "moran_i_medio": None, "moran_p_sim_medio": None, "moran_meses_signif": None,
            }
            pesos = entry.get("pesos")
            estabilidade = entry.get("estabilidade_variaveis")

            conn.execute(stmt, {
                "animal": animal, "metodo": metodo_key,
                "tipo_periodo": TIPO_PERIODO_LABELS[tipo_periodo],
                "data_processamento": now,
                "tmi": int(min(meta["train_periods"])), "tmf": int(max(meta["train_periods"])),
                "temi": int(min(meta["test_periods"])), "temf": int(max(meta["test_periods"])),
                "tlm": int(meta["test_last_period"]), "fm": int(meta["forecast_period"]),
                "ntr": int(meta["n_train"]), "nte": int(meta["n_test"]),
                "sf": list(meta["selected_features"]),
                "mse": entry["mse"], "rmse": entry["rmse"], "mae": entry["mae"], "r2": entry["r2"],
                "gain": entry["gain_vs_media_municipal"],
                "gbwkm": entry.get("bandwidth_km"), "gbwk": entry.get("bandwidth_k"),
                "gtbw": entry.get("bandwidth_s"), "gttau": entry.get("tau"),
                "coef": json.dumps(pesos) if pesos is not None else None,
                "estab": json.dumps(estabilidade) if estabilidade is not None else None,
                "mi": moran["moran_i_medio"], "mp": moran["moran_p_sim_medio"], "ms": moran["moran_meses_signif"],
                "gobs": geojsons.get(f"{prefixo_geo}_obs") if prefixo_geo else None,
                "gpred": geojsons.get(f"{prefixo_geo}_pred") if prefixo_geo else None,
                "gres": geojsons.get(f"{prefixo_geo}_res") if prefixo_geo else None,
                "gfc": geojsons.get(f"{prefixo_geo}_forecast") if prefixo_geo else None,
            })