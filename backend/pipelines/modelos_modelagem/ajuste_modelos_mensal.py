import pandas as pd
import numpy as np
import warnings
from datetime import datetime
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LassoCV
import statsmodels.api as sm

from libpysal.weights import KNN
from esda.moran import Moran

from modelos_modelagem.utils_modelagem import *
from modelos_modelagem.gwr import *
from modelos_modelagem.gtwr import *

warnings.filterwarnings("ignore")

EARTH_KM = 6371.0088

# ---------------------------------------------------------------------------
# Split treino/teste
# ---------------------------------------------------------------------------

def split_train(model_df, inicio_treino, fim_treino, inicio_teste, fim_teste):
    model_df["anomes_int"] = model_df["anomes"].astype(int)

    train_df = model_df.loc[model_df["anomes_int"].between(inicio_treino, fim_treino)].copy()
    test_df  = model_df.loc[model_df["anomes_int"].between(inicio_teste,  fim_teste)].copy()

    if train_df.empty or test_df.empty:
        raise ValueError(
            f"Split inválido: n_train={len(train_df)}, n_test={len(test_df)}. "
            "Verifique se existem observações nesses períodos."
        )

    train_months = sorted(train_df["anomes_int"].unique())
    test_months  = sorted(test_df["anomes_int"].unique())
    n_total      = len(train_df) + len(test_df)

    print("\n" + "=" * 140)
    print("SPLIT FIXO")
    print("=" * 140)
    print(f"Treino : {min(train_months)} → {max(train_months)}  (n_meses={len(train_months)})")
    print(f"Teste  : {min(test_months)} → {max(test_months)}  (n_meses={len(test_months)})")
    print(f"n_train = {len(train_df):,}  ({100*len(train_df)/n_total:.2f}%)")
    print(f"n_test  = {len(test_df):,}  ({100*len(test_df)/n_total:.2f}%)")

    return train_df, test_df, len(train_df), len(test_df), train_months, test_months


# ---------------------------------------------------------------------------
# Helpers geográficos
# ---------------------------------------------------------------------------

def haversine_matrix(coords_a, coords_b):
    """Calcula a distância (em km) entre dois conjuntos de coordenadas [lon, lat]."""
    a = np.radians(np.atleast_2d(np.asarray(coords_a, float)))
    b = np.radians(np.atleast_2d(np.asarray(coords_b, float)))
    lon1, lat1 = a[:, 0][:, None], a[:, 1][:, None]
    lon2, lat2 = b[:, 0][None, :], b[:, 1][None, :]
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return EARTH_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def _build_test_geo(df_pred, pred_col, last_month):
    cols = ["id_municipio", "anomes", "total_ocorrencias", "y_t", "y_next", pred_col]
    out = (
        df_pred.loc[df_pred["anomes"] == last_month, cols]
        .rename(columns={"y_t": "observado", pred_col: "predito"})
        .copy()
    )
    out[["observado", "predito", "total_ocorrencias"]] = (
        out[["observado", "predito", "total_ocorrencias"]].astype(float)
    )
    out["residuo"] = out["y_next"].astype(float) - out["predito"]
    return out.drop(columns=["y_next"]).set_index("id_municipio").sort_index()

def _build_forecast_geo(forecast_df, yhat, metodo, forecast_month):
    return (
        pd.DataFrame({
            "id_municipio":      forecast_df["id_municipio"].values,
            "anomes":            forecast_month,
            "predito":           np.maximum(0, np.asarray(yhat, dtype=float)),
            "total_ocorrencias": forecast_df["total_ocorrencias"].astype(float).values,
            "metodo":            metodo,
        })
        .set_index("id_municipio")
        .sort_index()
    )


def anomes_to_month_index(anomes_series):
    s    = anomes_series.astype(int)
    idx  = (s // 100) * 12 + (s % 100 - 1)
    return idx.max() - idx


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def fit_mensal(
    df,
    target:         str,
    forecast_month: int,
    drop_columns:   list = None,
    inicio_treino:  int = 202601,
    fim_treino:     int = 202604,
    inicio_teste:   int = 202201,
    fim_teste:      int = 202512,
    top_k:                    int = 20,
    rolling_window_months:    int = 6,
    rolling_min_train_months: int = 3,
):
    from libpysal.weights import full2W
    from esda.moran import Moran

    # ─────────────────────────────────────────────────────────────────────────
    # 1. PRÉ-PROCESSAMENTO E SPLIT
    # ─────────────────────────────────────────────────────────────────────────
    df_model = df.copy()
    df_model[target] = (
        pd.to_numeric(df_model[target], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )
    df_model["anomes"] = pd.to_numeric(df_model["anomes"], errors="coerce").astype("Int64")
    df_model = (
        df_model
        .dropna(subset=["id_municipio", "anomes"])
        .sort_values(["id_municipio", "anomes"])
    )
    df_model = feature_engineering(df_model)

    model_df = df_model.dropna(subset=["y_next"]).copy()
    candidate_features = (
        model_df
        .drop(columns=drop_columns or [], errors="ignore")
        .select_dtypes(include=[np.number])
        .columns.tolist()
    )
    print("N features candidatas:", len(candidate_features))

    train_df, test_df, n_train, n_test, train_months, test_months = split_train(
        model_df, inicio_treino, fim_treino, inicio_teste, fim_teste
    )
    test_last_month = max(test_months)

    forecast_df = df_model.loc[df_model["anomes"].astype(int) == forecast_month].copy()
    if forecast_df.empty:
        raise ValueError(f"Nenhuma linha encontrada para forecast_month={forecast_month}.")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. BASELINES
    # ─────────────────────────────────────────────────────────────────────────
    y_true       = test_df["y_next"].astype(float).values
    yhat_zero    = np.zeros_like(y_true)
    yhat_persist = test_df["y_t"].astype(float).values

    mun_mean      = train_df.groupby("id_municipio")["y_t"].mean()
    yhat_hist     = test_df["id_municipio"].map(mun_mean).fillna(mun_mean.mean()).astype(float).values

    # ─────────────────────────────────────────────────────────────────────────
    # 3. SELEÇÃO TEMPORAL POR ROLLING WINDOW + OLS GLOBAL
    # Cada mês de validação é previsto somente a partir de meses anteriores.
    # A seleção final contém as variáveis mais estáveis entre as janelas.
    # ─────────────────────────────────────────────────────────────────────────
    train_months_sorted = sorted(int(m) for m in train_months)
    if rolling_window_months < rolling_min_train_months:
        raise ValueError("rolling_window_months deve ser >= rolling_min_train_months.")

    rolling_records = []
    feature_frequency = {}
    for pos in range(rolling_min_train_months, len(train_months_sorted)):
        validation_month = train_months_sorted[pos]
        window_start = max(0, pos - rolling_window_months)
        fit_months = train_months_sorted[window_start:pos]

        fold_train = train_df.loc[train_df["anomes"].astype(int).isin(fit_months)].copy()
        fold_valid = train_df.loc[train_df["anomes"].astype(int) == validation_month].copy()
        if fold_train.empty or fold_valid.empty:
            continue

        fold_sel = fit_predict_lasso_base_models(
            fold_train,
            fold_valid,
            candidate_features,
            target_col="y_next",
            top_k=top_k,
            verbose=False
        )
        fold_features = fold_sel["selected_features"]
        for feature in fold_features:
            feature_frequency[feature] = feature_frequency.get(feature, 0) + 1

        rolling_records.append({
            "mes_validacao": validation_month,
            "meses_treino": fit_months,
            "n_train": len(fold_train),
            "n_valid": len(fold_valid),
            "mse_validacao": float(np.mean((fold_valid["y_next"].astype(float).values - fold_sel["yhat_ols"]) ** 2)),
            "n_features": len(fold_features),
            "features": fold_features,
        })

    if not rolling_records:
        raise ValueError(
            "Não há janelas temporais suficientes para a seleção rolling. "
            "Reduza rolling_min_train_months ou amplie o período de treino."
        )

    selected_features = [
        feature
        for feature, _ in sorted(
            feature_frequency.items(), key=lambda item: (-item[1], item[0])
        )[:top_k]
    ]
    if not selected_features:
        raise ValueError("A seleção rolling não reteve nenhuma variável.")

    # Reajuste final: usa todo o treino, mas apenas as variáveis selecionadas
    # sem acesso aos rótulos do período de teste.
    sel = fit_predict_lasso_base_models(
        train_df,
        test_df,
        selected_features,
        target_col="y_next",
        top_k=len(selected_features),
    )
    yhat_ols = sel["yhat_ols"]
    selected_features = sel["selected_features"]
    rolling_selection_df = pd.DataFrame(rolling_records)

    print("\n" + "=" * 140)
    print("SELEÇÃO ROLLING WINDOW — LASSO + OLS GLOBAL")
    print("=" * 140)
    print(
        rolling_selection_df[
            ["mes_validacao", "meses_treino", "n_train", "n_valid", "mse_validacao", "n_features"]
        ].round(4).to_string(index=False)
    )
    print(f"\nJanelas válidas: {len(rolling_selection_df)}")
    print(f"Coefs ≠ 0 no reajuste final: {sel['lasso_nonzero']}")
    print(f"Selecionadas por estabilidade (top {top_k}): {selected_features}")

    # Forecast OLS
    X_fc_raw = forecast_df[selected_features].replace([np.inf, -np.inf], np.nan)
    X_fc_ols = pd.DataFrame(sel["imputer"].transform(X_fc_raw), columns=selected_features, index=forecast_df.index)
    X_fc_ols = sm.add_constant(X_fc_ols, has_constant="add")
    yhat_ols_forecast = np.maximum(0, sel["ols"].predict(X_fc_ols).astype(float))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. MODELOS ESPACIAIS (GWR, GWRA, GTWR)
    # ─────────────────────────────────────────────────────────────────────────
    coords_fc = forecast_df[["longitude", "latitude"]].astype(float).values
    times_fc  = anomes_to_month_index(forecast_df["anomes"])

    gwr_kwargs  = dict(selected_features=selected_features, coord_cols=("longitude", "latitude"), bw_max_iter=15, verbose=True)

    # GWR Fixo
    gwr_out  = fit_predict_gwr(train_df=train_df, test_df=test_df, kernel="gaussian", search="grid", **gwr_kwargs)
    yhat_gwr = np.asarray(gwr_out["yhat"], dtype=float)
    yhat_gwr_forecast = np.maximum(0, gwr_out["gwr_model"].predict(
        gwr_out["imputer"].transform(X_fc_raw), coords_fc
    ))
    print(f"\nBandwidth GWR: {gwr_out['bandwidth_km']:.4f} km | LOOCV-MSE: {gwr_out['loocv_mse']:.6f}")

    # GWR Adaptativo
    gwra_out  = fit_predict_gwr(train_df=train_df, test_df=test_df, kernel="gaussian", adaptive=True, bw_tol=1.0, **{k: v for k, v in gwr_kwargs.items() if k != "bw_tol"})
    yhat_gwra = np.asarray(gwra_out["yhat"], dtype=float)
    yhat_gwra_forecast = np.maximum(0, gwra_out["gwr_model"].predict(
        gwra_out["imputer"].transform(X_fc_raw), coords_fc
    ))
    bandwidth_s = gwra_out.get('bandwidth_k')  

    # GTWR Gaussiano 
    gtwr_kwargs = {
        "selected_features": selected_features,
        "coord_cols": ("longitude", "latitude"),
        "time_col": "anomes",
        "verbose": False
    }

    gtwrgauss_out  = fit_predict_gtwr(
        train_df=train_df, 
        test_df=test_df, 
        fixed_bw_s=bandwidth_s,    
        search_method="golden",    
        **gtwr_kwargs
    )
    
    yhat_gtwrgauss = np.asarray(gtwrgauss_out["yhat"], dtype=float)
    yhat_gtwrgauss_forecast = np.maximum(0, gtwrgauss_out["gtwr_model"].predict(
        gtwrgauss_out["imputer"].transform(X_fc_raw), coords_fc, times_fc
    ))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. ÍNDICE DE MORAN PARA OS RESÍDUOS (TODOS OS MODELOS)
    # ─────────────────────────────────────────────────────────────────────────
    bw_s = float(gwr_out["bandwidth_km"])

    def gaussian_weights(D, bw):
        W = np.exp(-0.5 * (D / bw) ** 2)
        np.fill_diagonal(W, 0.0)
        return W

    def moran_por_mes(residuals, nome_modelo):
        base = test_df[["id_municipio", "anomes", "latitude", "longitude"]].copy()
        base["anomes"]   = base["anomes"].astype(int)
        base["residual"] = np.asarray(residuals, float)

        registros = []
        for mes, g in base.groupby("anomes"):
            if len(g) < 3: 
                continue
            coords_m = g[["longitude", "latitude"]].values
            resid_m  = g["residual"].values

            D = haversine_matrix(coords_m, coords_m)
            W = gaussian_weights(D, bw_s)
            rs = W.sum(axis=1, keepdims=True); rs[rs == 0] = 1.0
            W = W / rs
            W[np.isnan(W)] = 0.0

            w = full2W(W)
            w.transform = "R"

            mi = Moran(resid_m, w)
            registros.append({
                "modelo":  nome_modelo,
                "anomes":  int(mes),
                "moran_I": mi.I,
                "p_sim":   mi.p_sim,
            })
        return pd.DataFrame(registros)

    print("\nCalculando Índice de Moran para os resíduos de todos os modelos...")
    
    moran_dfs = [
        moran_por_mes(y_true - yhat_ols, "OLS"),
        moran_por_mes(y_true - yhat_gwr, "GWR"),
        moran_por_mes(y_true - yhat_gwra, "GWR_ADAPTATIVO"),
        moran_por_mes(y_true - yhat_gtwrgauss, "GTWR")
    ]
    
    moran_por_mes_df = pd.concat(moran_dfs, ignore_index=True)

    moran_resumo = (
        moran_por_mes_df
        .groupby("modelo")
        .agg(moran_I_medio=("moran_I", "mean"),
             p_sim_medio=("p_sim", "mean"),
             meses_signif=("p_sim", lambda s: int((s < 0.05).sum())),
             n_meses=("p_sim", "size"))
        .reset_index()
    )

    print("\n>> Resumo do Índice de Moran (Média):")
    print(moran_resumo.round(4).to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # 6. MÉTRICAS DE PERFORMANCE
    # ─────────────────────────────────────────────────────────────────────────
    test_period_label = f"{min(test_months)}-{max(test_months)}"
    modelos = [
        ("Baseline zero",            yhat_zero,      0),
        ("Baseline persistência",    yhat_persist,   0),
        ("Baseline média municipal", yhat_hist,      0),
        ("OLS Global",               yhat_ols,       len(selected_features)),
        ("GWR (Gaussiano)",          yhat_gwr,       len(selected_features)),
        ("GWR-Adaptativo",           yhat_gwra,      len(selected_features)),
        ("GTWR - Gaussiano",         yhat_gtwrgauss, len(selected_features)),
    ]

    df_eval = pd.DataFrame([
        calc_metrics(y_true, yhat, modelo=nome, test_period=test_period_label,
                     n_train=n_train, n_test=n_test, n_features=n_feat)
        for nome, yhat, n_feat in modelos
    ])
    
    mse_hist = df_eval.loc[df_eval["modelo"] == "Baseline média municipal", "MSE"].iloc[0]
    df_eval["gain_vs_media_municipal"] = (mse_hist - df_eval["MSE"]) / mse_hist
    df_eval = df_eval.sort_values("MSE").reset_index(drop=True)

    print("\n" + "=" * 140)
    print("RESULTADO COMPARATIVO GERAL")
    print("=" * 140)
    print(df_eval.round(4).to_string(index=False))

    df_eval.round(4).to_csv(f'resultados_modelagem_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv', index=False)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. PREPARAÇÃO DO RETORNO E MAPAS
    # ─────────────────────────────────────────────────────────────────────────
    df_pred = test_df[["id_municipio", "anomes", "total_ocorrencias", "y_t", "y_next"]].copy()
    df_pred["anomes"] = df_pred["anomes"].astype(int)

    for col, yhat in [
        ("pred_zero",            yhat_zero),
        ("pred_persistencia",    yhat_persist),
        ("pred_media_municipal", yhat_hist),
        ("pred_ols",             yhat_ols),
        ("pred_gwr",             yhat_gwr),
        ("pred_gwr_adaptativo",  yhat_gwra),
        ("pred_gtwr",            yhat_gtwrgauss),
    ]:
        df_pred[col] = yhat
        if col.startswith("pred_ols") or col.startswith("pred_gwr") or col.startswith("pred_gtwr"):
            df_pred[col.replace("pred_", "erro_")] = df_pred["y_next"] - yhat

    return {
        "meta": {
            "train_months":      train_months,
            "test_months":       test_months,
            "test_last_month":   test_last_month,
            "forecast_month":    forecast_month,
            "n_train":           n_train,
            "n_test":            n_test,
            "selected_features": selected_features,
            "rolling_window_months": rolling_window_months,
            "rolling_min_train_months": rolling_min_train_months,
            "gwr_bandwidth_km":  gwr_out["bandwidth_km"],
        },
        "metricas": df_eval,
        "moran_resumo": moran_resumo,
        "selecao_rolling": rolling_selection_df,

        "geo_ols_teste":    _build_test_geo(df_pred, "pred_ols",            test_last_month),
        "geo_gwr_teste":    _build_test_geo(df_pred, "pred_gwr",            test_last_month),
        "geo_gwra_teste":   _build_test_geo(df_pred, "pred_gwr_adaptativo", test_last_month),
        "geo_gtwr_teste":   _build_test_geo(df_pred, "pred_gtwr",           test_last_month),

        "geo_ols_forecast":  _build_forecast_geo(forecast_df, yhat_ols_forecast,       "ols_global",     forecast_month),
        "geo_gwr_forecast":  _build_forecast_geo(forecast_df, yhat_gwr_forecast,       "gwr",            forecast_month),
        "geo_gwra_forecast": _build_forecast_geo(forecast_df, yhat_gwra_forecast,      "gwr_adaptativo", forecast_month),
        "geo_gtwr_forecast": _build_forecast_geo(forecast_df, yhat_gtwrgauss_forecast, "gtwr",           forecast_month),

        "artifacts": {
            "gwra_bandwidth_k": bandwidth_s,
            "gtwr_bandwidth_s": gtwrgauss_out.get("bw_s"),
            "gtwr_tau":         gtwrgauss_out.get("tau")
        },
    }

