import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda.moran import Moran
from libpysal.weights import full2W
from mlxtend.feature_selection import SequentialFeatureSelector as SFS
from sklearn.linear_model import LassoCV, LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from modelos_modelagem.gwr import fit_predict_gwr
from modelos_modelagem.gtwr import fit_predict_gtwr
from modelos_modelagem.utils_modelagem import calc_metrics

warnings.filterwarnings("ignore")

ID = "id_municipio"
COORDS = ["longitude", "latitude"]
EARTH_KM = 6371.0088


def next_quarter(q):
    year, qtr = divmod(int(q), 10)
    if qtr not in (1, 2, 3, 4):
        raise ValueError(f"Trimestre inválido: {q}. Use AAAAT, ex.: 20261.")
    return (year + 1) * 10 + 1 if qtr == 4 else year * 10 + qtr + 1


def quarter_from_anomes(s):
    s = pd.to_numeric(s, errors="coerce").astype("Int64")
    year, month = s // 100, s % 100
    if (s.notna() & ~month.between(1, 12)).any():
        raise ValueError("Existem valores inválidos em anomes.")
    return (year * 10 + (month.sub(1) // 3 + 1)).astype("Int64")


def quarter_end_month(q):
    year, qtr = divmod(int(q), 10)
    return year * 100 + 3 * qtr


def month_index(s, reference):
    s = pd.to_numeric(s, errors="coerce").astype(int)
    idx = (s // 100) * 12 + s % 100 - 1
    ref = (int(reference) // 100) * 12 + int(reference) % 100 - 1
    return (ref - idx).to_numpy()


def prepare_data(df, target, time_col="trimestre", month_col="anomes"):
    """O painel deve ter uma linha por município/trimestre."""
    missing = {ID, target, *COORDS} - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")

    data = df.copy()
    if time_col not in data:
        if month_col not in data:
            raise ValueError(f"Informe '{time_col}' ou '{month_col}'.")
        data[time_col] = quarter_from_anomes(data[month_col])
    else:
        data[time_col] = pd.to_numeric(data[time_col], errors="coerce").astype("Int64")

    data[target] = pd.to_numeric(data[target], errors="coerce").replace([np.inf, -np.inf], np.nan)
    data = data.dropna(subset=[ID, time_col, target]).copy()
    data[time_col] = data[time_col].astype(int)

    if data.duplicated([ID, time_col]).any():
        raise ValueError(
            "Há mais de uma linha por município/trimestre. "
            "Agregue os dados mensais antes da modelagem."
        )

    data = data.sort_values([ID, time_col]).reset_index(drop=True)
    data["_gtwr_time"] = data[time_col].map(quarter_end_month)
    data["y_t"] = data[target].astype(float)

    g = data.groupby(ID, sort=False)
    data["y_next"] = g[target].shift(-1)
    actual_next = g[time_col].shift(-1)
    data.loc[actual_next.ne(data[time_col].map(next_quarter)), "y_next"] = np.nan

    return data, data.dropna(subset=["y_next"]).copy()


def get_features(df, target, time_col, drop_columns=None):
    excluded = {
        ID, time_col, "_gtwr_time", target, "y_t", "y_next",
        *COORDS, *(drop_columns or []),
    }
    return [
        c for c in df.select_dtypes(include=np.number)
        if c not in excluded and df[c].nunique(dropna=True) > 1
    ]


def iter_rolling_windows(df, n_quarters, time_col):
    periods = np.sort(df[time_col].unique())
    if len(periods) <= n_quarters:
        raise ValueError(
            f"rolling_window_quarters={n_quarters}, mas há somente {len(periods)} períodos com y_next."
        )

    for i in range(n_quarters, len(periods)):
        train_periods = periods[i - n_quarters:i]
        test_period = int(periods[i])

        sequence = [int(train_periods[0])]
        for _ in range(n_quarters):
            sequence.append(next_quarter(sequence[-1]))
        if list(map(int, train_periods)) != sequence[:-1] or test_period != sequence[-1]:
            continue

        train = df[df[time_col].isin(train_periods)].copy()
        test = df[df[time_col].eq(test_period)].copy()
        if not train.empty and not test.empty:
            yield train_periods, test_period, train, test


# -----------------------------------------------------------------------------
# Seleção e estabilidade
# -----------------------------------------------------------------------------

def clean_window(train, test, features, target="y_next"):
    usable = [
        c for c in features
        if c in train and train[c].notna().any() and train[c].nunique(dropna=True) > 1
    ]
    if not usable:
        return train.iloc[:0], test.iloc[:0], []

    train, test = train.copy(), test.copy()
    train[usable] = train[usable].replace([np.inf, -np.inf], np.nan)
    test[usable] = test[usable].replace([np.inf, -np.inf], np.nan)
    medians = train[usable].median()
    train[usable] = train[usable].fillna(medians)
    test[usable] = test[usable].fillna(medians)
    return train.dropna(subset=[target]), test.dropna(subset=[target]), usable


def select_features(X, y, top_k=20, cv=5):
    if X.empty or len(y) < 3:
        return []

    cv = max(2, min(cv, len(y)))
    lasso = make_pipeline(
        StandardScaler(),
        LassoCV(cv=cv, max_iter=20_000, random_state=42),
    ).fit(X, y)

    coef = lasso.named_steps["lassocv"].coef_
    keep = X.columns[np.abs(coef) > 1e-8].tolist()
    if not keep:
        return []

    sfs = SFS(
        LinearRegression(),
        k_features=(1, min(top_k, len(keep))),
        forward=True,
        floating=False,
        scoring="neg_mean_squared_error",
        cv=cv,
        n_jobs=-1,
    ).fit(X[keep], y)
    return list(sfs.k_feature_names_)


def design(df, features):
    X = df[features].astype(float) if features else pd.DataFrame(index=df.index)
    return sm.add_constant(X, has_constant="add")


def fit_ols(train, test, features):
    Xtr, Xte = design(train, features), design(test, features)
    model = sm.OLS(train["y_next"].astype(float), Xtr).fit()
    pred = np.asarray(model.predict(Xte[Xtr.columns]), float)
    metrics = {
        "mae": mean_absolute_error(test["y_next"], pred),
        "rmse": np.sqrt(mean_squared_error(test["y_next"], pred)),
        "aic": model.aic,
    }
    return model, np.maximum(0, pred), metrics


def stability_rows(train, test, selected, test_period):
    model, _, full = fit_ols(train, test, selected)
    rows = []
    for var in selected:
        _, _, reduced = fit_ols(train, test, [x for x in selected if x != var])
        rows.append({
            "test_origem": test_period,
            "variavel": var,
            "coef": model.params[var],
            "pvalor": model.pvalues[var],
            "mae_gain": reduced["mae"] - full["mae"],
            "rmse_gain": reduced["rmse"] - full["rmse"],
            "aic_gain": reduced["aic"] - full["aic"],
        })
    return rows


def summarize_stability(
    rows,
    n_windows,
    min_frequency=.50,
    min_sign_stability=.80,
    max_mean_pvalue=.10,
    max_cv=1.0,
):
    if not rows or not n_windows:
        return pd.DataFrame()

    out = pd.DataFrame(rows).groupby("variavel").agg(
        n_selecionada=("test_origem", "nunique"),
        coef_medio=("coef", "mean"),
        coef_mediano=("coef", "median"),
        coef_std=("coef", "std"),
        pvalor_medio=("pvalor", "mean"),
        perc_positivo=("coef", lambda x: (x > 0).mean()),
        perc_negativo=("coef", lambda x: (x < 0).mean()),
        avg_mae_gain=("mae_gain", "mean"),
        avg_rmse_gain=("rmse_gain", "mean"),
        avg_aic_gain=("aic_gain", "mean"),
    ).reset_index()

    out["n_windows_total"] = n_windows
    out["frequencia_selecao"] = out["n_selecionada"] / n_windows
    out["estabilidade_sinal"] = out[["perc_positivo", "perc_negativo"]].max(axis=1)
    out["cv_coef"] = out["coef_std"] / out["coef_medio"].abs().replace(0, np.nan)

    stable = out[
        out["frequencia_selecao"].ge(min_frequency)
        & out["estabilidade_sinal"].ge(min_sign_stability)
        & out["pvalor_medio"].le(max_mean_pvalue)
        & out["cv_coef"].fillna(0).le(max_cv)
    ].copy()

    cols = [
        "variavel", "frequencia_selecao", "estabilidade_sinal",
        "coef_medio", "coef_mediano", "coef_std", "cv_coef", "pvalor_medio",
        "avg_mae_gain", "avg_rmse_gain", "avg_aic_gain",
        "n_selecionada", "n_windows_total", "perc_positivo", "perc_negativo",
    ]
    return stable[cols].sort_values(
        ["frequencia_selecao", "estabilidade_sinal", "avg_rmse_gain"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


# -----------------------------------------------------------------------------
# Modelos espaciais e Moran
# -----------------------------------------------------------------------------

def fit_spatial(train, test, features):
    common = dict(
        selected_features=features,
        coord_cols=tuple(COORDS),
        kernel="gaussian",
        bw_max_iter=15,
    )
    gwr = fit_predict_gwr(train_df=train, test_df=test, search="grid", verbose=False, **common)
    gwra = fit_predict_gwr(
        train_df=train, test_df=test, adaptive=True, bw_tol=1.0, verbose=False, **common
    )
    gtwr = fit_predict_gtwr(
        train_df=train,
        test_df=test,
        selected_features=features,
        coord_cols=tuple(COORDS),
        time_col="_gtwr_time",
        fixed_bw_s=gwra.get("bandwidth_k"),
        search_method="golden",
        verbose=False,
    )
    pred = {
        "GWR (Gaussiano)": np.maximum(0, np.asarray(gwr["yhat"], float)),
        "GWR-Adaptativo": np.maximum(0, np.asarray(gwra["yhat"], float)),
        "GTWR - Gaussiano": np.maximum(0, np.asarray(gtwr["yhat"], float)),
    }
    return pred, gwr, gwra, gtwr


def haversine_matrix(coords):
    x = np.radians(np.asarray(coords, float))
    lon, lat = x[:, 0], x[:, 1]
    dlon, dlat = lon[None, :] - lon[:, None], lat[None, :] - lat[:, None]
    h = np.sin(dlat / 2) ** 2 + np.cos(lat[:, None]) * np.cos(lat[None, :]) * np.sin(dlon / 2) ** 2
    return EARTH_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


def moran_rows(test, predictions, bandwidth, quarter):
    if len(test) < 3 or bandwidth is None or not np.isfinite(bandwidth):
        return []

    D = haversine_matrix(test[COORDS].values)
    W = np.exp(-.5 * (D / float(bandwidth)) ** 2)
    np.fill_diagonal(W, 0)
    s = W.sum(1, keepdims=True)
    W = np.divide(W, s, out=np.zeros_like(W), where=s != 0)
    w = full2W(W)
    w.transform = "R"

    y = test["y_next"].to_numpy(float)
    return [
        {
            "modelo": name,
            "trimestre": quarter,
            "moran_I": (mi := Moran(y - np.asarray(pred, float), w)).I,
            "p_sim": mi.p_sim,
        }
        for name, pred in predictions.items()
    ]


# -----------------------------------------------------------------------------
# Rolling backtest
# -----------------------------------------------------------------------------

def run_rolling_backtest(model_df, features, n_quarters, top_k=20, cv=5, time_col="trimestre"):
    selections, frames, windows, moran = [], [], [], []

    for train_periods, test_period, train, test in iter_rolling_windows(
        model_df, n_quarters, time_col
    ):
        train, test, usable = clean_window(train, test, features)
        if train.empty or test.empty or not usable:
            continue

        selected = select_features(train[usable], train["y_next"], top_k, cv)
        if not selected:
            continue

        selections += stability_rows(train, test, selected, test_period)
        _, pred_ols, _ = fit_ols(train, test, selected)
        spatial_pred, gwr, _, _ = fit_spatial(train, test, selected)

        y = test["y_next"].to_numpy(float)
        mun_mean = train.groupby(ID)["y_t"].mean()
        preds = {
            "Baseline zero": np.zeros_like(y),
            "Baseline persistência": test["y_t"].to_numpy(float),
            "Baseline média municipal": test[ID].map(mun_mean).fillna(mun_mean.mean()).to_numpy(float),
            "OLS Global": pred_ols,
            **spatial_pred,
        }

        frame = test[[ID, time_col, *COORDS]].rename(columns={time_col: "trimestre_origem"}).copy()
        if "total_ocorrencias" in test:
            frame["total_ocorrencias"] = test["total_ocorrencias"].values
        frame["trimestre_alvo"] = next_quarter(test_period)
        frame["observado"] = y
        for col, name in {
            "pred_zero": "Baseline zero",
            "pred_persistencia": "Baseline persistência",
            "pred_media_municipal": "Baseline média municipal",
            "pred_ols": "OLS Global",
            "pred_gwr": "GWR (Gaussiano)",
            "pred_gwra": "GWR-Adaptativo",
            "pred_gtwr": "GTWR - Gaussiano",
        }.items():
            frame[col] = preds[name]
        frames.append(frame)

        model_preds = {k: v for k, v in preds.items() if not k.startswith("Baseline")}
        moran += moran_rows(test, model_preds, gwr.get("bandwidth_km"), next_quarter(test_period))
        windows.append({
            "train_inicio": int(train_periods[0]),
            "train_fim": int(train_periods[-1]),
            "test_origem": test_period,
            "test_alvo": next_quarter(test_period),
            "n_train": len(train),
            "n_test": len(test),
            "n_features": len(selected),
            "variaveis": selected,
        })

    if not frames:
        raise ValueError("Nenhuma rolling window pôde ser ajustada.")

    return {
        "predicoes": pd.concat(frames, ignore_index=True),
        "selecao": selections,
        "janelas": pd.DataFrame(windows),
        "moran": pd.DataFrame(moran),
    }


def evaluate_rolling(pred, windows):
    model_cols = {
        "Baseline zero": "pred_zero",
        "Baseline persistência": "pred_persistencia",
        "Baseline média municipal": "pred_media_municipal",
        "OLS Global": "pred_ols",
        "GWR (Gaussiano)": "pred_gwr",
        "GWR-Adaptativo": "pred_gwra",
        "GTWR - Gaussiano": "pred_gtwr",
    }
    y = pred["observado"].to_numpy(float)
    n_train = int(windows["n_train"].mean())
    n_features = int(windows["n_features"].mean())
    period = f"{pred['trimestre_alvo'].min()}-{pred['trimestre_alvo'].max()}"

    out = pd.DataFrame([
        calc_metrics(
            y, pred[col].to_numpy(float), modelo=name, test_period=period,
            n_train=n_train, n_test=len(pred),
            n_features=0 if name.startswith("Baseline") else n_features,
        )
        for name, col in model_cols.items()
    ])
    mse_ref = out.loc[out["modelo"].eq("Baseline média municipal"), "MSE"].iloc[0]
    out["gain_vs_media_municipal"] = (mse_ref - out["MSE"]) / mse_ref
    return out.sort_values("MSE").reset_index(drop=True)


def summarize_moran(detail):
    if detail.empty:
        return detail
    return detail.groupby("modelo").agg(
        moran_I_medio=("moran_I", "mean"),
        p_sim_medio=("p_sim", "mean"),
        trimestres_signif=("p_sim", lambda x: int((x < .05).sum())),
        n_trimestres=("p_sim", "size"),
    ).reset_index()


# -----------------------------------------------------------------------------
# Forecast final
# -----------------------------------------------------------------------------

def fit_final_forecast(train, forecast, features, time_col="trimestre"):
    Xtr, Xfc = design(train, features), design(forecast, features)
    ols = sm.OLS(train["y_next"].astype(float), Xtr).fit()
    pred_ols = np.maximum(0, np.asarray(ols.predict(Xfc[Xtr.columns]), float))

    # test_df é obrigatório nas funções espaciais; aqui serve apenas para obter
    # os objetos ajustados. O forecast é calculado explicitamente abaixo.
    validation = train[train[time_col].eq(train[time_col].max())]
    _, gwr, gwra, gtwr = fit_spatial(train, validation, features)

    Xfc_raw = forecast[features].replace([np.inf, -np.inf], np.nan)
    coords = forecast[COORDS].to_numpy(float)
    pred = {
        "pred_ols": pred_ols,
        "pred_gwr": np.maximum(0, gwr["gwr_model"].predict(gwr["imputer"].transform(Xfc_raw), coords)),
        "pred_gwra": np.maximum(0, gwra["gwr_model"].predict(gwra["imputer"].transform(Xfc_raw), coords)),
        "pred_gtwr": np.maximum(0, gtwr["gtwr_model"].predict(
            gtwr["imputer"].transform(Xfc_raw),
            coords,
            month_index(forecast["_gtwr_time"], train["_gtwr_time"].max()),
        )),
    }
    artifacts = {
        "ols_model": ols,
        "gwr_bandwidth_km": gwr.get("bandwidth_km"),
        "gwra_bandwidth_k": gwra.get("bandwidth_k"),
        "gtwr_bandwidth_s": gtwr.get("bw_s"),
        "gtwr_tau": gtwr.get("tau"),
    }
    return pred, artifacts


# -----------------------------------------------------------------------------
# Pipeline principal
# -----------------------------------------------------------------------------

def fit_trimestral(
    df,
    target,
    time_col="trimestre",
    month_col="anomes",
    drop_columns=None,
    rolling_window_quarters=4,
    top_k=20,
    cv=5,
    min_frequency=.50,
    min_sign_stability=.80,
    max_mean_pvalue=.10,
    max_cv=1.0,
    save_csv=False,
    output_dir=".",
):
    """
    Treino/teste, estabilidade e forecast seguem a mesma rolling window.

    Ex.: rolling_window_quarters=4
        20221-20224 -> teste origem 20231 -> prevê 20232
        20222-20231 -> teste origem 20232 -> prevê 20233
        ...
    """
    full, model_df = prepare_data(df, target, time_col, month_col)
    features = get_features(model_df, target, time_col, drop_columns)
    if not features:
        raise ValueError("Nenhuma variável candidata disponível.")

    rolling = run_rolling_backtest(
        model_df, features, rolling_window_quarters, top_k, cv, time_col
    )
    stability = summarize_stability(
        rolling["selecao"],
        len(rolling["janelas"]),
        min_frequency,
        min_sign_stability,
        max_mean_pvalue,
        max_cv,
    )
    if stability.empty:
        raise ValueError("Nenhuma variável satisfez os critérios de estabilidade.")

    selected = stability["variavel"].tolist()
    metrics = evaluate_rolling(rolling["predicoes"], rolling["janelas"])
    moran_summary = summarize_moran(rolling["moran"])

    # Último trimestre observado é a origem do forecast.
    model_periods = np.sort(model_df[time_col].unique())
    full_periods = np.sort(full[time_col].unique())
    forecast_origin = int(full_periods[-1])
    if forecast_origin != next_quarter(int(model_periods[-1])):
        raise ValueError("O histórico final não é trimestral e contínuo.")

    final_periods = model_periods[-rolling_window_quarters:]
    final_train = model_df[model_df[time_col].isin(final_periods)].copy()
    forecast = full[full[time_col].eq(forecast_origin)].copy()

    # Imputação da janela final usando somente medianas do treino.
    final_train, forecast_tmp, usable = clean_window(
        final_train, forecast.assign(y_next=0.0), selected
    )
    selected = [x for x in selected if x in usable]
    if not selected:
        raise ValueError("Variáveis estáveis indisponíveis na janela final.")
    forecast = forecast_tmp.drop(columns="y_next", errors="ignore")

    final_pred, artifacts = fit_final_forecast(final_train, forecast, selected, time_col)
    forecast_out = forecast[[ID, time_col, *COORDS]].rename(
        columns={time_col: "trimestre_origem"}
    ).copy()
    if "total_ocorrencias" in forecast:
        forecast_out["total_ocorrencias"] = forecast["total_ocorrencias"].values
    forecast_out["trimestre"] = next_quarter(forecast_origin)
    for col, values in final_pred.items():
        forecast_out[col] = values

    if save_csv:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        metrics.to_csv(path / f"metricas_rolling_{stamp}.csv", index=False)
        stability.to_csv(path / f"estabilidade_{stamp}.csv", index=False)
        rolling["predicoes"].to_csv(path / f"predicoes_rolling_{stamp}.csv", index=False)
        forecast_out.to_csv(path / f"forecast_trimestral_{stamp}.csv", index=False)

    return {
        "meta": {
            "rolling_window_quarters": rolling_window_quarters,
            "n_windows": len(rolling["janelas"]),
            "selected_features": selected,
            "forecast_origin": forecast_origin,
            "forecast_quarter": next_quarter(forecast_origin),
            "final_train_quarters": final_periods.tolist(),
        },
        "metricas": metrics,
        "predicoes_rolling": rolling["predicoes"],
        "janelas_rolling": rolling["janelas"],
        "estabilidade_variaveis": stability,
        "moran_por_trimestre": rolling["moran"],
        "moran_resumo": moran_summary,
        "forecast": forecast_out.set_index(ID).sort_index(),
        "artifacts": artifacts,
    }