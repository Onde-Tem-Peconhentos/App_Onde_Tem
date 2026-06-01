import pandas as pd
import numpy as np
import math

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

import statsmodels.api as sm
import warnings

from modelos_modelagem.utils_modelagem import *
from modelos_modelagem.gwr import *

warnings.filterwarnings("ignore")

drop_cols = [
    "id_municipio", "anomes", "y_next",
    "total_ocorrencias", "incidencia", "smr",
]


def split_train(model_df):
    model_df["anomes_int"] = model_df["anomes"].astype(int)

    train_mask = model_df["anomes_int"].between(202601, 202604)
    test_mask  = model_df["anomes_int"].between(202501, 202512)

    train_df = model_df.loc[train_mask].copy()
    test_df  = model_df.loc[test_mask].copy()

    if len(train_df) == 0 or len(test_df) == 0:
        raise ValueError(
            f"Split inválido: n_train={len(train_df)}, n_test={len(test_df)}. "
            "Verifique se existem observações nesses períodos."
        )

    n_train      = len(train_df)
    n_test       = len(test_df)
    n_total      = n_train + n_test
    train_months = sorted(train_df["anomes_int"].unique().tolist())
    test_months  = sorted(test_df["anomes_int"].unique().tolist())

    print("\n" + "=" * 140)
    print("SPLIT FIXO")
    print("=" * 140)
    print(f"Treino : {min(train_months)} → {max(train_months)}  (n_meses={len(train_months)})")
    print(f"Teste  : {min(test_months)} → {max(test_months)}  (n_meses={len(test_months)})")
    print(f"n_train = {n_train:,}  ({100*n_train/n_total:.2f}%)")
    print(f"n_test  = {n_test:,}  ({100*n_test/n_total:.2f}%)")

    return train_df, test_df, n_train, n_test, train_months, test_months


def _build_test_geo(df_pred, pred_col, test_last_month):
    """Último mês de teste → DataFrame com observado/predito/residuo, index=id_municipio."""
    cols = ["id_municipio", "anomes", "y_next", pred_col]
    out = (
        df_pred.loc[df_pred["anomes"] == test_last_month, cols]
        .rename(columns={"y_next": "observado", pred_col: "predito"})
        .copy()
    )
    out["observado"] = out["observado"].astype(float)
    out["predito"]   = out["predito"].astype(float)
    out["residuo"]   = out["observado"] - out["predito"]
    return out.set_index("id_municipio").sort_index()


def _build_forecast_geo(forecast_df, yhat, metodo, forecast_month):
    """Mês de previsão → DataFrame com predito, index=id_municipio."""
    return (
        pd.DataFrame({
            "id_municipio": forecast_df["id_municipio"].values,
            "anomes":       forecast_month,
            "predito":      np.maximum(0, np.asarray(yhat, dtype=float)),
            "metodo":       metodo,
        })
        .set_index("id_municipio")
        .sort_index()
    )


def fit(df, forecast_month: int):
    """
    Treina OLS e GWR, avalia no período de teste (2025) e gera
    os DataFrames prontos para build_geojson.

    Args:
        df             : DataFrame bruto vindo do banco.
        forecast_month : Mês de previsão no formato YYYYMM (ex: 202605).

    Returns:
        dict com as chaves:
            meta, metricas, predicoes_teste_completo,
            geo_ols_teste, geo_gwr_teste,
            geo_ols_forecast, geo_gwr_forecast,
            artifacts
    """
    # ── 1. Limpeza e feature engineering ─────────────────────────────────────
    df_model = df.copy()
    df_model["total_ocorrencias"] = (
        pd.to_numeric(df_model["total_ocorrencias"], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )
    df_model["anomes"] = pd.to_numeric(df_model["anomes"], errors="coerce").astype("Int64")
    df_model = (
        df_model
        .dropna(subset=["id_municipio", "anomes"])
        .sort_values(["id_municipio", "anomes"])
        .copy()
    )
    df_model = feature_engineering(df_model)

    # ── 2. Base modelável ─────────────────────────────────────────────────────
    model_df = df_model.dropna(subset=["y_next"]).copy()
    candidate_features = (
        model_df
        .drop(columns=drop_cols, errors="ignore")
        .select_dtypes(include=[np.number])
        .columns
        .tolist()
    )
    print("N features candidatas:", len(candidate_features))

    # ── 3. Split ──────────────────────────────────────────────────────────────
    train_df, test_df, n_train, n_test, train_months, test_months = split_train(model_df)
    test_last_month = max(test_months)   # 202512

    # ── 4. DataFrame do mês de previsão ───────────────────────────────────────
    forecast_df = df_model.loc[
        df_model["anomes"].astype(int) == forecast_month
    ].copy()

    if forecast_df.empty:
        raise ValueError(
            f"Nenhuma linha encontrada para forecast_month={forecast_month}. "
            "Verifique se o mês existe no DataFrame."
        )

    # ── 5. Baselines ──────────────────────────────────────────────────────────
    y_true       = test_df["y_next"].astype(float).values
    yhat_zero    = np.zeros_like(y_true, dtype=float)
    yhat_persist = test_df["y_t"].astype(float).values

    mun_mean_train    = train_df.groupby("id_municipio")["y_t"].mean()
    global_mean_train = train_df["y_t"].mean()
    yhat_hist = (
        test_df["id_municipio"]
        .map(mun_mean_train)
        .fillna(global_mean_train)
        .astype(float)
        .values
    )

    # ── 6. Lasso + OLS ────────────────────────────────────────────────────────
    top_k     = 20
    model_out = fit_predict_lasso_ols(
        train_df=train_df,
        test_df=test_df,
        candidate_features=candidate_features,
        top_k=top_k,
    )
    yhat_lasso_ols     = np.asarray(model_out["yhat"], dtype=float)
    selected_features  = model_out["selected_features"]

    print("\n" + "=" * 140)
    print("LASSO — SELEÇÃO DE VARIÁVEIS")
    print("=" * 140)
    print(f"alpha ótimo : {model_out['lasso_alpha']:.6f}")
    print(f"Coefs ≠ 0   : {model_out['lasso_nonzero']}")
    print(f"Selecionadas (top {top_k}): {selected_features}")

    coef_display = (
        model_out["coef_lasso"][model_out["coef_lasso"] != 0]
        .sort_values(key=lambda s: s.abs(), ascending=False)
        .head(top_k)
        .reset_index()
    )
    coef_display.columns = ["feature", "lasso_coef"]
    print("\nCoeficientes Lasso (escala padronizada):")
    print(coef_display.to_string(index=False))
    print("\nResumo OLS (HC3):")
    print(model_out["ols"].summary())

    # Previsão OLS para o mês atual
    X_fc_raw = forecast_df[selected_features].replace([np.inf, -np.inf], np.nan)
    X_fc_ols = model_out["scaler"].transform(model_out["imputer"].transform(X_fc_raw))
    X_fc_ols = pd.DataFrame(X_fc_ols, columns=selected_features, index=forecast_df.index)
    X_fc_ols = sm.add_constant(X_fc_ols, has_constant="add")
    yhat_ols_forecast = np.maximum(0, np.asarray(model_out["ols"].predict(X_fc_ols), dtype=float))

    # ── 7. GWR ───────────────────────────────────────────────────────────────
    gwr_out = fit_predict_gwr(
        train_df=train_df,
        test_df=test_df,
        selected_features=selected_features,
        coord_cols=("longitude", "latitude"),
        kernel="gaussian",
        ridge=1e-6,
        bw_min=None,
        bw_max=None,
        bw_tol=5.0,
        bw_max_iter=15,
        verbose=True,
    )
    yhat_gwr = np.asarray(gwr_out["yhat"], dtype=float)

    print(f"\nBandwidth ótimo GWR : {gwr_out['bandwidth_km']:.4f} km")
    print(f"LOOCV-MSE GWR treino: {gwr_out['loocv_mse']:.6f}")
    print("\nHistórico golden search:")
    print(gwr_out["bw_history"].to_string(index=False))

    # Previsão GWR para o mês atual
    X_fc_gwr = gwr_out["scaler"].transform(gwr_out["imputer"].transform(X_fc_raw))
    coords_fc = forecast_df[["longitude", "latitude"]].astype(float).values
    yhat_gwr_forecast = np.maximum(0, gwr_out["gwr_model"].predict(X_fc_gwr, coords_fc))

    # ── 8. Métricas ───────────────────────────────────────────────────────────
    test_period_label = f"{min(test_months)}-{max(test_months)}"
    eval_rows = []
    for nome, yhat, n_feat in [
        ("Baseline zero",            yhat_zero,      0),
        ("Baseline persistência",    yhat_persist,   0),
        ("Baseline média municipal", yhat_hist,      0),
        (f"Lasso + OLS top {top_k}", yhat_lasso_ols, len(selected_features)),
        ("GWR",                      yhat_gwr,       len(selected_features)),
    ]:
        eval_rows.append(calc_metrics(
            y_true, yhat,
            modelo=nome,
            test_period=test_period_label,
            n_train=n_train,
            n_test=n_test,
            n_features=n_feat,
        ))

    df_eval = pd.DataFrame(eval_rows)
    mse_hist = df_eval.loc[df_eval["modelo"] == "Baseline média municipal", "MSE"].iloc[0]
    df_eval["gain_vs_media_municipal"] = (mse_hist - df_eval["MSE"]) / mse_hist
    df_eval = df_eval.sort_values("MSE").reset_index(drop=True)

    print("\n" + "=" * 140)
    print("RESULTADO COMPARATIVO — OLS vs GWR (mesmas features Lasso)")
    print("=" * 140)
    print(
        df_eval.round({
            "MSE": 4, "RMSE": 4, "MAE": 4, "R2": 4,
            "gain_vs_media_municipal": 4,
        }).to_string(index=False)
    )

    # ── 9. Predições detalhadas do teste ──────────────────────────────────────
    df_pred = test_df[["id_municipio", "anomes", "total_ocorrencias", "y_next"]].copy()
    df_pred["anomes"]               = df_pred["anomes"].astype(int)
    df_pred["pred_zero"]            = yhat_zero
    df_pred["pred_persistencia"]    = yhat_persist
    df_pred["pred_media_municipal"] = yhat_hist
    df_pred["pred_lasso_ols"]       = yhat_lasso_ols
    df_pred["erro_lasso_ols"]       = df_pred["y_next"] - df_pred["pred_lasso_ols"]
    df_pred["pred_gwr"]             = yhat_gwr
    df_pred["erro_gwr"]             = df_pred["y_next"] - df_pred["pred_gwr"]

    # ── 10. DataFrames prontos para build_geojson ─────────────────────────────
    geo_ols_teste    = _build_test_geo(df_pred, "pred_lasso_ols", test_last_month)
    geo_gwr_teste    = _build_test_geo(df_pred, "pred_gwr",       test_last_month)
    geo_ols_forecast = _build_forecast_geo(forecast_df, yhat_ols_forecast, "ols", forecast_month)
    geo_gwr_forecast = _build_forecast_geo(forecast_df, yhat_gwr_forecast, "gwr", forecast_month)

    # ── 11. Artefatos ─────────────────────────────────────────────────────────
    artifacts = {
        "df_eval_split":     df_eval,
        "df_pred_split":     df_pred,
        "selected_features": selected_features,
        "coef_lasso":        coef_display,
        "ols_summary":       model_out["ols"].summary(),
        "gwr_bandwidth_km":  gwr_out["bandwidth_km"],
        "gwr_loocv_mse":     gwr_out["loocv_mse"],
        "gwr_bw_history":    gwr_out["bw_history"],
        # dicts completos — necessários para predict_new fora do fit()
        "gwr_out":           gwr_out,
        "model_out":         model_out,
    }

    # ── 12. Return ────────────────────────────────────────────────────────────
    return {
        "meta": {
            "train_months":      train_months,
            "test_months":       test_months,
            "test_last_month":   test_last_month,
            "forecast_month":    forecast_month,
            "n_train":           n_train,
            "n_test":            n_test,
            "top_k":             top_k,
            "selected_features": selected_features,
            "lasso_alpha":       model_out["lasso_alpha"],
            "gwr_bandwidth_km":  gwr_out["bandwidth_km"],
            "gwr_loocv_mse":     gwr_out["loocv_mse"],
        },
        "metricas":                  df_eval,
        "predicoes_teste_completo":  df_pred,
        "geo_ols_teste":             geo_ols_teste,
        "geo_gwr_teste":             geo_gwr_teste,
        "geo_ols_forecast":          geo_ols_forecast,
        "geo_gwr_forecast":          geo_gwr_forecast,
        "artifacts":                 artifacts,
    }