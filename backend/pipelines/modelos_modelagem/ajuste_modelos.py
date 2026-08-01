import pandas as pd
import numpy as np
import math

from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LassoCV

import statsmodels.api as sm
import warnings

from modelos_modelagem.utils_modelagem import *
from modelos_modelagem.gwr import *
from modelos_modelagem.gtwr import *

warnings.filterwarnings("ignore")

drop_cols = [
    "id_municipio", "anomes", "y_next",
    "total_ocorrencias", "incidencia", "smr",
]

def fit_predict_lasso_ols(train_df, test_df, candidate_features, top_k=15):
    """
    LassoCV para seleção de variáveis + OLS.
    Retorna dicionário com yhat, objetos de preprocessing e metadados.
    """
    X_train = train_df[candidate_features].copy()
    X_test  = test_df[candidate_features].copy()

    y_train = train_df["y_next"].astype(float).values
    y_test  = test_df["y_next"].astype(float).values

    X_train = X_train.replace([np.inf, -np.inf], np.nan)
    X_test  = X_test.replace([np.inf, -np.inf], np.nan)

    # --- Lasso para seleção de variáveis ---
    lasso_selector = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler",  StandardScaler()),
        ("lasso",   LassoCV(cv=5, max_iter=100_000, tol=1e-3, n_jobs=-1, random_state=42)),
    ])
    lasso_selector.fit(X_train, y_train)

    lasso = lasso_selector.named_steps["lasso"]
    coef_lasso = pd.Series(lasso.coef_, index=candidate_features)

    lasso_alpha = float(getattr(lasso, "alpha_", np.nan))
    lasso_nonzero = int((coef_lasso != 0).sum())

    coef_nonzero = (
        coef_lasso[coef_lasso != 0]
        .sort_values(key=lambda s: s.abs(), ascending=False)
    )
    selected_features = coef_nonzero.head(top_k).index.tolist()

    if len(selected_features) == 0:
        selected_features = ["y_t"] if "y_t" in candidate_features else candidate_features[:1]

    # --- OLS robusto ---
    X_train_sel = X_train[selected_features].copy()
    X_test_sel  = X_test[selected_features].copy()

    imputer = SimpleImputer(strategy="median")
    scaler  = StandardScaler()

    X_train_imp = imputer.fit_transform(X_train_sel)
    X_train_sc  = scaler.fit_transform(X_train_imp)

    # manter índices originais para compatibilidade
    X_train_sc = pd.DataFrame(X_train_sc, columns=selected_features, index=train_df.index)
    X_test_sc  = pd.DataFrame(
        scaler.transform(imputer.transform(X_test_sel)),
        columns=selected_features, index=test_df.index
    )

    X_train_ols = sm.add_constant(X_train_sc, has_constant="add")
    X_test_ols  = sm.add_constant(X_test_sc,  has_constant="add")

    ols_model = sm.OLS(y_train, X_train_ols).fit()
    yhat = np.maximum(0, ols_model.predict(X_test_ols).astype(float))

    return {
        "yhat": yhat,
        "selected_features": selected_features,
        "lasso_alpha": lasso_alpha,
        "lasso_nonzero": lasso_nonzero,
        "coef_lasso": coef_lasso,
        "ols": ols_model,
        "imputer": imputer,
        "scaler": scaler,
    }

def split_train(
    model_df,
    inicio_treino,
    fim_treino,
    inicio_teste,
    fim_teste,
):
    model_df["anomes_int"] = model_df["anomes"].astype(int)

    train_mask = model_df["anomes_int"].between(inicio_treino, fim_treino)
    test_mask  = model_df["anomes_int"].between(inicio_teste,  fim_teste)

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


def fit(
    df,
    forecast_month: int,
    inicio_treino:  int = 202601,
    fim_treino:     int = 202604,
    inicio_teste:   int = 202201,
    fim_teste:      int = 202512,
):
    """
    Treina OLS, GWR fixo e GWR adaptativo, avalia no período de teste e gera
    os DataFrames prontos para build_geojson.

    Args:
        df             : DataFrame bruto vindo do banco.
        forecast_month : Mês de previsão no formato YYYYMM (ex: 202605).
        inicio_treino  : Primeiro mês do treino  (YYYYMM, default 202601).
        fim_treino     : Último  mês do treino   (YYYYMM, default 202604).
        inicio_teste   : Primeiro mês do teste   (YYYYMM, default 202201).
        fim_teste      : Último  mês do teste    (YYYYMM, default 202512).

    Returns:
        dict com as chaves:
            meta, metricas, predicoes_teste_completo,
            geo_ols_teste, geo_gwr_teste, geo_gwra_teste,
            geo_ols_forecast, geo_gwr_forecast, geo_gwra_forecast,
            artifacts
    """
    # ── Limpeza e feature engineering ─────────────────────────────────────
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

    # ── Base modelável ─────────────────────────────────────────────────────
    model_df = df_model.dropna(subset=["y_next"]).copy()
    candidate_features = (
        model_df
        .drop(columns=drop_cols, errors="ignore")
        .select_dtypes(include=[np.number])
        .columns
        .tolist()
    )
    print("N features candidatas:", len(candidate_features))

    # ── Split ──────────────────────────────────────────────────────────────
    train_df, test_df, n_train, n_test, train_months, test_months = split_train(
        model_df,
        inicio_treino=inicio_treino,
        fim_treino=fim_treino,
        inicio_teste=inicio_teste,
        fim_teste=fim_teste,
    )
    test_last_month = max(test_months)   

    # ── DataFrame do mês de previsão ───────────────────────────────────────
    forecast_df = df_model.loc[
        df_model["anomes"].astype(int) == forecast_month
    ].copy()

    if forecast_df.empty:
        raise ValueError(
            f"Nenhuma linha encontrada para forecast_month={forecast_month}. "
            "Verifique se o mês existe no DataFrame."
        )

    # ── Baselines ──────────────────────────────────────────────────────────
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

    # ── Lasso + OLS ────────────────────────────────────────────────────────
    top_k     = 20
    model_selection_output = fit_predict_lasso_ols(
        train_df=train_df,
        test_df=test_df,
        candidate_features=candidate_features,
        top_k=top_k,
    )
    yhat_lasso_ols     = np.asarray(model_selection_output["yhat"], dtype=float)
    selected_features  = model_selection_output["selected_features"]

    print("\n" + "=" * 140)
    print("LASSO — SELEÇÃO DE VARIÁVEIS")
    print("=" * 140)
    print(f"alpha ótimo : {model_selection_output['lasso_alpha']:.6f}")
    print(f"Coefs ≠ 0   : {model_selection_output['lasso_nonzero']}")
    print(f"Selecionadas (top {top_k}): {selected_features}")

    coef_display = (
        model_selection_output["coef_lasso"][model_selection_output["coef_lasso"] != 0]
        .sort_values(key=lambda s: s.abs(), ascending=False)
        .head(top_k)
        .reset_index()
    )
    coef_display.columns = ["feature", "lasso_coef"]
    print("\nCoeficientes Lasso (escala padronizada):")
    print(coef_display.to_string(index=False))
    print("\nResumo OLS:")
    print(model_selection_output["ols"].summary())

    # Previsão OLS para o mês atual
    X_fc_raw = forecast_df[selected_features].replace([np.inf, -np.inf], np.nan)
    X_fc_ols = model_selection_output["imputer"].transform(X_fc_raw)
    X_fc_ols = pd.DataFrame(X_fc_ols, columns=selected_features, index=forecast_df.index)
    X_fc_ols = sm.add_constant(X_fc_ols, has_constant="add")
    yhat_ols_forecast = np.maximum(0, np.asarray(model_selection_output["ols"].predict(X_fc_ols), dtype=float))

    # ── GWR ───────────────────────────────────────────────────────────────
    gwr_out = fit_predict_gwr(
        train_df=train_df,
        test_df=test_df,
        selected_features=selected_features,
        coord_cols=("longitude", "latitude"),
        kernel="gaussian",
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

    # Previsão GWR fixo para o mês de forecast
    X_fc_gwr  = gwr_out["imputer"].transform(X_fc_raw)
    coords_fc = forecast_df[["longitude", "latitude"]].astype(float).values
    yhat_gwr_forecast = np.maximum(0, gwr_out["gwr_model"].predict(X_fc_gwr, coords_fc))

    # ── GWR Adaptativo ────────────────────────────────────────────────────
    gwra_out = fit_predict_gwr(
        train_df=train_df,
        test_df=test_df,
        selected_features=selected_features,
        coord_cols=("longitude", "latitude"),
        kernel="gaussian",
        adaptive=True,
        bw_min=None,
        bw_max=None,
        bw_tol=1.0,
        bw_max_iter=15,
        verbose=True,
    )
    yhat_gwra = np.asarray(gwra_out["yhat"], dtype=float)

    print(f"\nBandwidth ótimo GWR-Adaptativo : {int(gwra_out['bandwidth_k'])} vizinhos")
    print(f"LOOCV-MSE GWR-Adaptativo treino: {gwra_out['loocv_mse']:.6f}")
    print("\nHistórico golden search (adaptativo):")
    print(gwra_out["bw_history"].to_string(index=False))

    # Previsão GWR adaptativo para o mês de forecast
    X_fc_gwra = gwra_out["imputer"].transform(X_fc_raw)
    yhat_gwra_forecast = np.maximum(0, gwra_out["gwr_model"].predict(X_fc_gwra, coords_fc))

    # ── Métricas ───────────────────────────────────────────────────────────
    test_period_label = f"{min(test_months)}-{max(test_months)}"
    eval_rows = []
    for nome, yhat, n_feat in [
        ("Baseline zero",            yhat_zero,      0),
        ("Baseline persistência",    yhat_persist,   0),
        ("Baseline média municipal", yhat_hist,      0),
        ("OLS",                      yhat_lasso_ols, len(selected_features)),
        ("GWR",                      yhat_gwr,       len(selected_features)),
        ("GWR-Adaptativo",           yhat_gwra,      len(selected_features)),
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
    print("RESULTADO COMPARATIVO — OLS vs GWR vs GWR-Adaptativo (mesmas features Lasso)")
    print("=" * 140)
    print(
        df_eval.round({
            "MSE": 4, "RMSE": 4, "MAE": 4, "R2": 4,
            "gain_vs_media_municipal": 4,
        }).to_string(index=False)
    )

    # ── Predições detalhadas do teste ──────────────────────────────────────
    df_pred = test_df[["id_municipio", "anomes", "total_ocorrencias", "y_next"]].copy()
    df_pred["anomes"]               = df_pred["anomes"].astype(int)
    df_pred["pred_zero"]            = yhat_zero
    df_pred["pred_persistencia"]    = yhat_persist
    df_pred["pred_media_municipal"] = yhat_hist
    df_pred["pred_lasso_ols"]       = yhat_lasso_ols
    df_pred["erro_lasso_ols"]       = df_pred["y_next"] - df_pred["pred_lasso_ols"]
    df_pred["pred_gwr"]             = yhat_gwr
    df_pred["erro_gwr"]             = df_pred["y_next"] - df_pred["pred_gwr"]
    df_pred["pred_gwr_adaptativo"]  = yhat_gwra
    df_pred["erro_gwr_adaptativo"]  = df_pred["y_next"] - df_pred["pred_gwr_adaptativo"]

    # ── DataFrames prontos para build_geojson ─────────────────────────────
    geo_ols_teste     = _build_test_geo(df_pred, "pred_lasso_ols",      test_last_month)
    geo_gwr_teste     = _build_test_geo(df_pred, "pred_gwr",            test_last_month)
    geo_gwra_teste    = _build_test_geo(df_pred, "pred_gwr_adaptativo", test_last_month)
    geo_ols_forecast  = _build_forecast_geo(forecast_df, yhat_ols_forecast,  "ols",            forecast_month)
    geo_gwr_forecast  = _build_forecast_geo(forecast_df, yhat_gwr_forecast,  "gwr",            forecast_month)
    geo_gwra_forecast = _build_forecast_geo(forecast_df, yhat_gwra_forecast, "gwr_adaptativo", forecast_month)

    # ── Artefatos ─────────────────────────────────────────────────────────
    artifacts = {
        "df_eval_split":     df_eval,
        "df_pred_split":     df_pred,
        "selected_features": selected_features,
        "coef_lasso":        coef_display,
        "ols_summary":       model_selection_output["ols"].summary(),
        "gwr_bandwidth_km":  gwr_out["bandwidth_km"],
        "gwr_loocv_mse":     gwr_out["loocv_mse"],
        "gwr_bw_history":    gwr_out["bw_history"],
        # dicts completos — necessários para predict_new fora do fit()
        "gwr_out":           gwr_out,
        "model_selection_output":         model_selection_output,
    }

    # ── Return ────────────────────────────────────────────────────────────
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
            "lasso_alpha":       model_selection_output["lasso_alpha"],
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