import numpy as np
import pandas as pd
import statsmodels.api as sm
from mlxtend.feature_selection import SequentialFeatureSelector as SFS
from sklearn.linear_model import LassoCV, LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from modelos_modelagem.gwr import (
    fit_predict_gwr,
    GeographicallyWeightedRegression,
)
from modelos_modelagem.gtwr import (
    fit_predict_gtwr,
    GeographicallyTemporallyWeightedRegression,
    anomes_to_month_index,
)

ID = "id_municipio"
COORDS = ["longitude", "latitude"]
POP = "populacao"


def _period_offset(tipo):
    return {"mes": pd.offsets.MonthBegin(1), "trimestre": pd.offsets.QuarterBegin(startingMonth=1),
            "semestre": pd.DateOffset(months=6), "ano": pd.offsets.YearBegin(1)}[tipo]


def _periods_per_year(tipo):
    return {"mes": 12, "trimestre": 4, "semestre": 2, "ano": 1}[tipo]


def _next_period(p, tipo):
    return pd.Timestamp(p) + _period_offset(tipo)


def _prepare(df, target, period_col, tipo):
    required = {ID, target, period_col, POP, *COORDS}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Colunas ausentes: {sorted(missing)}")

    d = df.copy()
    d[period_col] = pd.to_datetime(d[period_col])
    d = d.sort_values([ID, period_col]).reset_index(drop=True)
    if d.duplicated([ID, period_col]).any():
        raise ValueError("A base deve ter uma linha por município/período.")

    d[target] = pd.to_numeric(d[target], errors="coerce")
    d[POP] = pd.to_numeric(d[POP], errors="coerce")
    d = d.dropna(subset=[ID, period_col, target, POP, *COORDS]).copy()

    g = d.groupby(ID, sort=False)
    d["y_next"] = g[target].shift(-1)
    d["pop_next"] = g[POP].shift(-1)
    d["periodo_next"] = g[period_col].shift(-1)
    expected = d[period_col].map(lambda x: _next_period(x, tipo))
    bad = d["periodo_next"].ne(expected)
    d.loc[bad, ["y_next", "pop_next"]] = np.nan

    # tempo contínuo em meses; funciona para GTWR em qualquer periodicidade.
    base = d[period_col].min()
    d["_time"] = (d[period_col].dt.year - base.year) * 12 + d[period_col].dt.month - base.month
    d["_gtwr_time"] = d[period_col].dt.year * 100 + d[period_col].dt.month
    return d


def _candidate_features(df, target, period_col, drop_columns=None):
    excluded = {ID, target, period_col, POP, "y_next", "pop_next", "periodo_next", "_time", "_gtwr_time",
                *COORDS, *(drop_columns or [])}
    return [c for c in df.select_dtypes(include=np.number)
            if c not in excluded and df[c].nunique(dropna=True) > 1]


def _clean(train, test, features):
    usable = [c for c in features if c in train and train[c].notna().any()
              and train[c].nunique(dropna=True) > 1]
    train, test = train.copy(), test.copy()
    med = train[usable].replace([np.inf, -np.inf], np.nan).median()
    train[usable] = train[usable].replace([np.inf, -np.inf], np.nan).fillna(med)
    test[usable] = test[usable].replace([np.inf, -np.inf], np.nan).fillna(med)
    return train, test, usable


def _select(X, y, top_k=20, cv=5):
    cv = max(2, min(cv, len(y)))
    lasso = make_pipeline(StandardScaler(), LassoCV(cv=cv, max_iter=20000, random_state=42)).fit(X, y)
    keep = X.columns[np.abs(lasso.named_steps["lassocv"].coef_) > 1e-8].tolist()
    if not keep:
        return []
    sfs = SFS(LinearRegression(), k_features=(1, min(top_k, len(keep))), forward=True,
              floating=False, scoring="neg_mean_squared_error", cv=cv, n_jobs=-1).fit(X[keep], y)
    return list(sfs.k_feature_names_)


def _stable_features(model_df, features, window_periods, period_col, min_frequency=.5, top_k=20, cv=5):
    periods = np.sort(model_df[period_col].dropna().unique())
    rows, n_windows = [], 0
    for i in range(window_periods, len(periods)):
        train_p, test_p = periods[i-window_periods:i], periods[i]
        train = model_df[model_df[period_col].isin(train_p)].copy()
        test = model_df[model_df[period_col].eq(test_p)].copy()
        train, test, usable = _clean(train, test, features)
        train, test = train.dropna(subset=["y_next"]), test.dropna(subset=["y_next"])
        if train.empty or test.empty or not usable:
            continue
        selected = _select(train[usable], train["y_next"], top_k, cv)
        if not selected:
            continue
        n_windows += 1
        rows.extend({"variavel": v, "periodo": pd.Timestamp(test_p)} for v in selected)

    if not rows:
        raise ValueError("Nenhuma janela válida para seleção de variáveis.")
    s = (pd.DataFrame(rows).groupby("variavel").size().rename("n_selecionada").reset_index())
    s["n_janelas"] = n_windows
    s["frequencia"] = s["n_selecionada"] / n_windows
    stable = s[s["frequencia"] >= min_frequency].sort_values("frequencia", ascending=False)
    if stable.empty:
        raise ValueError("Nenhuma variável atingiu a frequência mínima de estabilidade.")
    return stable["variavel"].tolist(), stable.reset_index(drop=True)


def _target_to_count(y, pop, target_scale):
    y = np.maximum(0, np.asarray(y, float))
    pop = np.asarray(pop, float)
    if target_scale == "incidencia_100k":
        return y * pop / 100_000.0
    if target_scale == "contagem":
        return y
    raise ValueError("target_scale deve ser 'incidencia_100k' ou 'contagem'.")


def _metrics(y, pred, baseline):
    rmse = np.sqrt(mean_squared_error(y, pred))
    mae = mean_absolute_error(y, pred)
    r2 = r2_score(y, pred) if len(y) > 1 else np.nan
    base_rmse = np.sqrt(mean_squared_error(y, baseline))
    gain = 1 - rmse / base_rmse if base_rmse > 0 else np.nan
    return {"rmse": rmse, "mae": mae, "r2": r2, "ganho_baseline_historica": gain}


def _fit_backtest_models(train, test, features):
    """Otimiza hiperparâmetros e ajusta os três modelos no backtest."""
    Xtr = sm.add_constant(train[features], has_constant="add")
    Xte = sm.add_constant(test[features], has_constant="add").reindex(
        columns=Xtr.columns, fill_value=1.0
    )
    ols = sm.OLS(train["y_next"].astype(float), Xtr).fit()
    pred_ols = np.maximum(0, np.asarray(ols.predict(Xte), float))

    gwr = fit_predict_gwr(
        train, test,
        selected_features=features,
        coord_cols=tuple(COORDS),
        kernel="gaussian",
        search="grid",
        verbose=False,
    )

    gtwr = fit_predict_gtwr(
        train, test,
        selected_features=features,
        coord_cols=tuple(COORDS),
        time_col="_gtwr_time",
        search_method="golden",
        verbose=False,
    )

    return {
        "ols": {"pred": pred_ols, "fit": ols},
        "gwr": {"pred": np.maximum(0, np.asarray(gwr["yhat"], float)), "fit": gwr},
        "gtwr": {"pred": np.maximum(0, np.asarray(gtwr["yhat"], float)), "fit": gtwr},
    }


def _fit_forecast_models(train, forecast, features, backtest_models):
    """
    Reajusta os modelos incluindo o último período observado, mas NÃO repete
    a busca de hiperparâmetros espaciais.
    """
    # OLS
    Xtr = sm.add_constant(train[features], has_constant="add")
    Xfc = sm.add_constant(forecast[features], has_constant="add").reindex(
        columns=Xtr.columns, fill_value=1.0
    )
    ols = sm.OLS(train["y_next"].astype(float), Xtr).fit()
    pred_ols = np.maximum(0, np.asarray(ols.predict(Xfc), float))

    # GWR: reutiliza somente o bandwidth encontrado no backtest.
    gwr_bt = backtest_models["gwr"]["fit"]
    gwr_imputer = SimpleImputer(strategy="median")
    Xtr_gwr = gwr_imputer.fit_transform(
        train[features].replace([np.inf, -np.inf], np.nan)
    )
    Xfc_gwr = gwr_imputer.transform(
        forecast[features].replace([np.inf, -np.inf], np.nan)
    )
    coords_tr = train[COORDS].to_numpy(float)
    coords_fc = forecast[COORDS].to_numpy(float)

    gwr_model = GeographicallyWeightedRegression(
        bandwidth=gwr_bt["bandwidth_km"],
        kernel=gwr_bt.get("kernel", "gaussian"),
        adaptive=False,
    ).fit(Xtr_gwr, train["y_next"].to_numpy(float), coords_tr)
    pred_gwr = np.maximum(0, gwr_model.predict(Xfc_gwr, coords_fc))

    # GTWR: reutiliza bw_s e tau encontrados no backtest.
    gtwr_bt = backtest_models["gtwr"]["fit"]
    gtwr_imputer = SimpleImputer(strategy="median")
    Xtr_gtwr = gtwr_imputer.fit_transform(
        train[features].replace([np.inf, -np.inf], np.nan)
    )
    Xfc_gtwr = gtwr_imputer.transform(
        forecast[features].replace([np.inf, -np.inf], np.nan)
    )

    raw_train = train["_gtwr_time"].astype(int)
    month_train = (raw_train // 100) * 12 + (raw_train % 100 - 1)
    reference = int(month_train.max())
    t_train = anomes_to_month_index(train["_gtwr_time"], reference).to_numpy(float)
    t_forecast = anomes_to_month_index(forecast["_gtwr_time"], reference).to_numpy(float)

    gtwr_model = GeographicallyTemporallyWeightedRegression(
        bw_s=gtwr_bt["bw_s"],
        tau=gtwr_bt["tau"],
        kernel="gaussian",
        max_time_lag=None,
    ).fit(
        Xtr_gtwr,
        train["y_next"].to_numpy(float),
        coords_tr,
        t_train,
    )
    pred_gtwr = np.maximum(
        0, gtwr_model.predict(Xfc_gtwr, coords_fc, t_forecast)
    )

    return {
        "ols": {"pred": pred_ols, "fit": ols},
        "gwr": {
            "pred": pred_gwr,
            "fit": {
                "gwr_model": gwr_model,
                "imputer": gwr_imputer,
                "bandwidth_km": gwr_bt["bandwidth_km"],
                "kernel": gwr_bt.get("kernel", "gaussian"),
            },
        },
        "gtwr": {
            "pred": pred_gtwr,
            "fit": {
                "gtwr_model": gtwr_model,
                "imputer": gtwr_imputer,
                "bw_s": gtwr_bt["bw_s"],
                "tau": gtwr_bt["tau"],
            },
        },
    }


def _coef_summary(name, fitted, features):
    labels = ["intercepto", *features]
    if name == "ols":
        p = fitted.params
        return {"tipo": "global", "coeficientes": {k: float(v) for k, v in p.items()}}

    if name == "gwr":
        betas = np.vstack(list(fitted["gwr_model"].betas_.values()))
    else:
        betas = np.asarray(fitted["gtwr_model"].coef_, float)

    return {
        "tipo": "quartis_locais",
        "coeficientes": {
            label: {"q1": float(q[0]), "mediana": float(q[1]), "q3": float(q[2])}
            for label, q in zip(labels, np.quantile(betas, [.25, .5, .75], axis=0).T)
        },
    }


def fit_modelos(
    df,
    target="incidencia_100k",
    target_scale="incidencia_100k",
    period_col="dt_referencia",
    tipo_periodo="trimestre",
    rolling_window=4,
    min_frequency=.50,
    top_k=20,
    cv=5,
    drop_columns=None,
):
    """Seleciona variáveis por estabilidade, faz backtest no último período observado e forecast no seguinte."""
    data = _prepare(df, target, period_col, tipo_periodo)
    observed_periods = np.sort(data[period_col].unique())
    if len(observed_periods) < rolling_window + 3:
        raise ValueError("Histórico insuficiente para seleção, backtest e forecast.")

    backtest_period = pd.Timestamp(observed_periods[-1])
    forecast_period = _next_period(backtest_period, tipo_periodo)
    origin_backtest = pd.Timestamp(observed_periods[-2])

    # seleção usa apenas origens anteriores ao backtest, evitando vazamento.
    selection_df = data[(data[period_col] < origin_backtest) & data["y_next"].notna()].copy()
    features = _candidate_features(data, target, period_col, drop_columns)
    selected, stability = _stable_features(selection_df, features, rolling_window, period_col,
                                           min_frequency, top_k, cv)

    # BACKTEST: treina até duas origens antes e prevê o último período observado.
    train_bt = data[(data[period_col] < origin_backtest) & data["y_next"].notna()].copy()
    test_bt = data[data[period_col].eq(origin_backtest) & data["y_next"].notna()].copy()
    train_bt, test_bt, selected = _clean(train_bt, test_bt, selected)
    models_bt = _fit_backtest_models(train_bt, test_bt, selected)

    y_count = _target_to_count(test_bt["y_next"], test_bt["pop_next"], target_scale)
    hist_counts = _target_to_count(train_bt["y_next"], train_bt["pop_next"], target_scale)
    hist = pd.Series(hist_counts, index=train_bt.index).groupby(train_bt[ID]).mean()
    baseline = test_bt[ID].map(hist).fillna(float(np.mean(hist_counts))).to_numpy(float)

    metrics = [{
        "modelo": "baseline_historica",
        **_metrics(y_count, baseline, baseline),
    }]
    # A baseline é a referência: por definição seu ganho contra ela mesma é zero.
    metrics[0]["ganho_baseline_historica"] = 0.0

    backtest = {}
    for name, obj in models_bt.items():
        pred_count = _target_to_count(obj["pred"], test_bt["pop_next"], target_scale)
        metrics.append({"modelo": name, **_metrics(y_count, pred_count, baseline)})
        backtest[name] = pd.DataFrame({
            ID: test_bt[ID].values,
            "populacao": test_bt["pop_next"].values,
            "observado": y_count,
            "predito": pred_count,
        }).set_index(ID)

    # FORECAST: agora inclui a origem do backtest e prevê o próximo período não observado.
    train_fc = data[(data[period_col] < backtest_period) & data["y_next"].notna()].copy()
    test_fc = data[data[period_col].eq(backtest_period)].copy()
    train_fc, test_fc, selected = _clean(train_fc, test_fc, selected)
    models_fc = _fit_forecast_models(train_fc, test_fc, selected, models_bt)

    forecast, coeficientes = {}, {}
    for name, obj in models_fc.items():
        pred_count = _target_to_count(obj["pred"], test_fc[POP], target_scale)
        forecast[name] = pd.DataFrame({ID: test_fc[ID].values, "populacao": test_fc[POP].values,
                                       "predito": pred_count}).set_index(ID)
        coeficientes[name] = _coef_summary(name, obj["fit"], selected)

    return {
        "meta": {
            "tipo_periodo": tipo_periodo,
            "backtest_periodo": backtest_period.date().isoformat(),
            "forecast_periodo": forecast_period.date().isoformat(),
            "n_variaveis": len(selected),
            "variaveis_selecionadas": selected,
            "rolling_window": rolling_window,
        },
        "metricas": pd.DataFrame(metrics),
        "estabilidade": stability,
        "coeficientes": coeficientes,
        "backtest": backtest,
        "forecast": forecast,
    }