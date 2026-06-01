from datetime import datetime, timezone
from sqlalchemy import text
import numpy as np
import pandas as pd


def persist_results_mes(engine, animal: str, result: dict, geojsons: dict):
    """
    Persiste os resultados de OLS e GWR na tabela modelos.previsao.

    Parameters
    ----------
    engine   : SQLAlchemy engine
    animal   : nome do animal processado
    result   : dict retornado por fit()
    geojsons : dict com as chaves:
                 ols_obs, ols_pred, ols_res, ols_forecast,
                 gwr_obs, gwr_pred, gwr_res, gwr_forecast
    """

    ddl = """
    CREATE SCHEMA IF NOT EXISTS modelos;

    CREATE TABLE IF NOT EXISTS modelos.previsao (
        id                      SERIAL PRIMARY KEY,
        animal                  TEXT        NOT NULL,
        metodo                  TEXT        NOT NULL,
        data_processamento      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        tipo_periodo             TEXT       NOT NULL,
        train_month_inicio      INTEGER     NOT NULL,
        train_month_fim         INTEGER     NOT NULL,
        test_month_inicio       INTEGER     NOT NULL,
        test_month_fim          INTEGER     NOT NULL,
        test_last_month         INTEGER     NOT NULL,
        forecast_month          INTEGER     NOT NULL,
        n_train                 INTEGER     NOT NULL,
        n_test                  INTEGER     NOT NULL,
        n_features              INTEGER     NOT NULL,
        selected_features       TEXT[]      NOT NULL,
        mse                     DOUBLE PRECISION,
        rmse                    DOUBLE PRECISION,
        mae                     DOUBLE PRECISION,
        r2                      DOUBLE PRECISION,
        gain_vs_media_municipal DOUBLE PRECISION,
        lasso_alpha             DOUBLE PRECISION,
        gwr_bandwidth_km        DOUBLE PRECISION,
        gwr_loocv_mse           DOUBLE PRECISION,
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
    meta    = result["meta"]
    df_eval = result["metricas"]

    def _get_metrics(metodo_label: str) -> dict:
        row = df_eval.loc[df_eval["modelo"].str.contains(metodo_label, case=False)]
        if row.empty:
            return {
                "mse": None, "rmse": None, "mae": None,
                "r2": None, "gain": None
            }
        row = row.iloc[0]
        return {
            "mse":  float(row["MSE"]) if not pd.isna(row["MSE"]) else None,
            "rmse": float(row["RMSE"]) if not pd.isna(row["RMSE"]) else None,
            "mae":  float(row["MAE"]) if not pd.isna(row["MAE"]) else None,
            "r2":   float(row["R2"]) if not pd.isna(row["R2"]) else None,
            "gain": float(row["gain_vs_media_municipal"]) if not pd.isna(row["gain_vs_media_municipal"]) else None,
        }

    def _to_float(x):
        if x is None or pd.isna(x):
            return None
        return float(x)

    now = datetime.now(timezone.utc)

    rows = [
        {
            "metodo":                   "ols",
            "lasso_alpha":              _to_float(meta.get("lasso_alpha")),
            "gwr_bandwidth_km":         None,
            "gwr_loocv_mse":            None,
            "geojson_observado":        geojsons["ols_obs"],
            "geojson_predito":          geojsons["ols_pred"],
            "geojson_residuo":          geojsons["ols_res"],
            "geojson_forecast":         geojsons["ols_forecast"],
            **_get_metrics("OLS"),
        },
        {
            "metodo":                   "gwr",
            "lasso_alpha":              None,
            "gwr_bandwidth_km":         _to_float(meta.get("gwr_bandwidth_km")),
            "gwr_loocv_mse":            _to_float(meta.get("gwr_loocv_mse")),
            "geojson_observado":        geojsons["gwr_obs"],
            "geojson_predito":          geojsons["gwr_pred"],
            "geojson_residuo":          geojsons["gwr_res"],
            "geojson_forecast":         geojsons["gwr_forecast"],
            **_get_metrics("GWR"),
        },
    ]

    stmt = text("""
        INSERT INTO modelos.previsao (
            animal, metodo, tipo_periodo, data_processamento,
            train_month_inicio, train_month_fim,
            test_month_inicio,  test_month_fim,
            test_last_month,    forecast_month,
            n_train,            n_test,
            n_features,         selected_features,
            mse, rmse, mae, r2, gain_vs_media_municipal,
            lasso_alpha,        gwr_bandwidth_km,   gwr_loocv_mse,
            geojson_observado,  geojson_predito,
            geojson_residuo,    geojson_forecast
        ) VALUES (
            :animal, :metodo, :tipo_periodo, :data_processamento,
            :train_month_inicio, :train_month_fim,
            :test_month_inicio,  :test_month_fim,
            :test_last_month,    :forecast_month,
            :n_train,            :n_test,
            :n_features,         :selected_features,
            :mse, :rmse, :mae, :r2, :gain,
            :lasso_alpha,        :gwr_bandwidth_km,  :gwr_loocv_mse,
            :geojson_observado,  :geojson_predito,
            :geojson_residuo,    :geojson_forecast
        )
        ON CONFLICT (animal, metodo, forecast_month, data_processamento)
        DO NOTHING
    """)

    with engine.begin() as conn:
        for row in rows:
            conn.execute(stmt, {
                "animal":               animal,
                "metodo":               row["metodo"],
                "data_processamento":   now,
                "tipo_periodo":         "Mês",
                "train_month_inicio":   int(min(meta["train_months"])),
                "train_month_fim":      int(max(meta["train_months"])),
                "test_month_inicio":    int(min(meta["test_months"])),
                "test_month_fim":       int(max(meta["test_months"])),
                "test_last_month":      int(meta["test_last_month"]),
                "forecast_month":       int(meta["forecast_month"]),
                "n_train":              int(meta["n_train"]),
                "n_test":               int(meta["n_test"]),
                "n_features":           int(len(meta["selected_features"])),
                "selected_features":    list(meta["selected_features"]),  # converte para TEXT[]
                "mse":                  row["mse"],
                "rmse":                 row["rmse"],
                "mae":                  row["mae"],
                "r2":                   row["r2"],
                "gain":                 row["gain"],
                "lasso_alpha":          row["lasso_alpha"],
                "gwr_bandwidth_km":     row["gwr_bandwidth_km"],
                "gwr_loocv_mse":        row["gwr_loocv_mse"],
                "geojson_observado":    row["geojson_observado"],
                "geojson_predito":      row["geojson_predito"],
                "geojson_residuo":      row["geojson_residuo"],
                "geojson_forecast":     row["geojson_forecast"],
            })
