"""
ajuste_modelos_unificado.py — pipeline de ajuste único para todas as
periodicidades (mês, trimestre, semestre, ano).

Contexto: o repositório tinha uma implementação por periodicidade
(ajuste_modelos_mensal.py, ajuste_modelos_trimestral.py,
ajuste_modelos_anual.py — mantidas intactas, não usadas por este módulo) mais
uma tentativa antiga e genérica (ajuste_modelos.py, também mantida intacta)
que foi abandonada em favor da versão mensal dedicada (ver histórico de
`pipeline_modelagem.py`: `from modelos_modelagem.ajuste_modelos import fit`
→ `from modelos_modelagem.ajuste_modelos_mensal import fit_mensal`). Nenhuma
das três periodicidades além do mês chegou a ser conectada a um pipeline.

Este módulo generaliza a lógica da versão mensal (a mais recente e testada)
para qualquer periodicidade, em vez de reviver a tentativa genérica antiga,
mantendo o MESMO método de seleção de variáveis (Lasso temporal + stepwise
bidirecional por AIC, via `fit_predict_lasso_base_models`) para todas as
periodicidades — era esse o pedido: unificar sem introduzir um terceiro
método de seleção (a versão trimestral usava Lasso + SFS, diferente da
mensal).

Estratégia: os dados de entrada continuam vindo da MESMA query mensal já
validada (`query_modelagem` em pipeline_modelagem.py — uma linha por
município × mês). Para trimestre/semestre/ano, `aggregate_period()` agrega
esse painel mensal para a periodicidade alvo (mesmas regras de agregação já
usadas na CTE `base_trimestral`, hoje morta, do próprio pipeline_modelagem.py:
soma para acumulados de chuva/dias, média para temperatura/umidade/pressão/
radiação, extremos via max/min, atributos estáticos via max) e recalcula as
features de sazonalidade/tendência de forma genérica (`periods_per_year`
específico da periodicidade), em vez de simplesmente somar as colunas de
interação mensais (que não fazem sentido fora da escala mensal).

O núcleo de modelagem (seleção rolling-window, OLS, GWR, GWR-Adaptativo,
GTWR, Índice de Moran, métricas) é o mesmo de `fit_mensal`, generalizado para
operar sobre uma coluna de período genérica em vez de `anomes`.
"""

import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm
from libpysal.weights import full2W
from esda.moran import Moran
from xgboost import XGBRegressor

from modelos_modelagem.utils_modelagem import fit_predict_lasso_base_models, calc_metrics
from modelos_modelagem.gwr import fit_predict_gwr
from modelos_modelagem.gtwr import fit_predict_gtwr, anomes_to_month_index

warnings.filterwarnings("ignore")

EARTH_KM = 6371.0088
ID = "id_municipio"

# periodos_por_ano usado tanto para o ciclo sazonal (sin/cos) quanto para
# converter contagens de "quantidade de períodos" em algo comparável entre
# periodicidades diferentes.
PERIODS_PER_YEAR = {"mes": 12, "trimestre": 4, "semestre": 2, "ano": 1}
PERIOD_MONTHS = {"mes": 1, "trimestre": 3, "semestre": 6, "ano": 12}

# Colunas de identificação/target da query mensal que nunca são agregadas
# por soma/média — são recalculadas ou tratadas à parte.
_ID_COLS = {"id_municipio", "anomes", "dt_referencia", "total_ocorrencias", "incidencia_100k"}

# Atributos estáticos do município (não variam mês a mês) — carregados via
# MAX. Nomes padronizados em snake_case curto (ver pipeline_modelagem.py —
# a query SQL já entrega essas colunas com esses nomes; antes vinham
# misturadas com MAIUSCULAS vindas direto da tabela sz_municipios, o que
# acabava aparecendo cru nos cards de variável no frontend).
_STATIC_COLS = {
    "latitude", "longitude", "populacao",
    "idhm_renda", "idhm_saude", "idhm_educa", "idhm",
    "perc_pop_rural", "perc_pop_urbana", "pib", "n_favelas", "pop_favelas",
    "perc_apartamento", "perc_casa", "perc_vila_condominio", "perc_total_moradia",
    "dens_pop", "altitude", "area_vegetal", "veg_tipo",
    "perc_veg", "area_km2", "perc_homens",
    # Distâncias geográficas derivadas (calculadas em pipeline_modelagem.py a
    # partir das coordenadas do município e mescladas em df_modelos antes de
    # chegar aqui) — estáticas por município, mesma regra de agregação (MAX).
    "dist_capital_km", "dist_litoral_km",
}

# Colunas climáticas mensais e sua regra de agregação ao somar meses num
# período maior (mesmas regras já usadas na CTE base_trimestral do SQL).
_SUM_COLS = {"prec", "dias_chuva", "dias_calor"}
_MAX_COLS = {"seq_chuva", "tmax", "seq_calor", "umax"}
_MIN_COLS = {"tmin", "umin"}
_MEAN_COLS = {
    "prec_med", "temp", "amp_tmax", "amp_tmin", "amp_t", "umid", "amp_umax",
    "amp_u", "press", "rad",
}


def _quarter_of(month):
    return (month - 1) // 3 + 1


def _semester_of(month):
    return (month - 1) // 6 + 1


def _period_id(dt, tipo_periodo):
    """Identificador inteiro do período: mes->AAAAMM, trimestre->AAAAT (T=1..4),
    semestre->AAAAS (S=1..2), ano->AAAA."""
    y, m = dt.year, dt.month
    if tipo_periodo == "mes":
        return y * 100 + m
    if tipo_periodo == "trimestre":
        return y * 10 + _quarter_of(m)
    if tipo_periodo == "semestre":
        return y * 10 + _semester_of(m)
    if tipo_periodo == "ano":
        return y
    raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")


def _period_end_month(dt, tipo_periodo):
    """Último mês (AAAAMM) coberto pelo período — usado para alimentar o
    kernel temporal do GTWR (que espera um rótulo no formato AAAAMM)."""
    y, m = dt.year, dt.month
    if tipo_periodo == "mes":
        return y * 100 + m
    if tipo_periodo == "trimestre":
        end_m = _quarter_of(m) * 3
        return y * 100 + end_m
    if tipo_periodo == "semestre":
        end_m = _semester_of(m) * 6
        return y * 100 + end_m
    if tipo_periodo == "ano":
        return y * 100 + 12
    raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")


def next_period(periodo, tipo_periodo):
    """Próximo identificador de período no mesmo formato de `_period_id`."""
    if tipo_periodo == "mes":
        y, m = divmod(int(periodo), 100)
        return (y + 1) * 100 + 1 if m == 12 else y * 100 + m + 1
    if tipo_periodo == "trimestre":
        y, q = divmod(int(periodo), 10)
        return (y + 1) * 10 + 1 if q == 4 else y * 10 + q + 1
    if tipo_periodo == "semestre":
        y, s = divmod(int(periodo), 10)
        return (y + 1) * 10 + 1 if s == 2 else y * 10 + 2
    if tipo_periodo == "ano":
        return int(periodo) + 1
    raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")


def period_of_year(periodo, tipo_periodo):
    if tipo_periodo == "mes":
        return int(periodo) % 100
    if tipo_periodo in ("trimestre", "semestre"):
        return int(periodo) % 10
    return 1  # "ano": sem ciclo sazonal


# ---------------------------------------------------------------------------
# Agregação do painel mensal para a periodicidade alvo
# ---------------------------------------------------------------------------

def aggregate_period(df_mensal: pd.DataFrame, tipo_periodo: str) -> pd.DataFrame:
    """
    Agrega o painel mensal (`query_modelagem`, uma linha por município × mês)
    para a periodicidade alvo. Para tipo_periodo == "mes" apenas recalcula
    `periodo`/`periodo_fim_anomes` e devolve o painel praticamente intacto
    (mesmas colunas de features climáticas cruas), descartando as colunas de
    interação/sazonalidade mensal que serão recalculadas de forma genérica.
    """
    if tipo_periodo not in PERIODS_PER_YEAR:
        raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")

    d = df_mensal.copy()
    d["dt_referencia"] = pd.to_datetime(d["dt_referencia"])
    d["periodo"] = d["dt_referencia"].map(lambda x: _period_id(x, tipo_periodo))
    d["periodo_fim_anomes"] = d["dt_referencia"].map(lambda x: _period_end_month(x, tipo_periodo))

    keep_cols = [c for c in d.columns if c in _STATIC_COLS or c in _SUM_COLS
                 or c in _MAX_COLS or c in _MIN_COLS or c in _MEAN_COLS]

    if tipo_periodo == "mes":
        out = d[[ID, "periodo", "periodo_fim_anomes", "total_ocorrencias", *keep_cols]].copy()
        out["total_ocorrencias"] = out["total_ocorrencias"].astype(float)
    else:
        agg = {"total_ocorrencias": "sum", "periodo_fim_anomes": "max"}
        agg.update({c: "sum" for c in keep_cols if c in _SUM_COLS})
        agg.update({c: "max" for c in keep_cols if c in _MAX_COLS or c in _STATIC_COLS})
        agg.update({c: "min" for c in keep_cols if c in _MIN_COLS})
        agg.update({c: "mean" for c in keep_cols if c in _MEAN_COLS})

        out = (
            d.groupby([ID, "periodo"], as_index=False)
            .agg(agg)
        )

    out["incidencia_100k"] = (
        out["total_ocorrencias"].astype(float) * 100_000
        / out["populacao"].replace(0, np.nan)
    ).fillna(0.0)

    ppy = PERIODS_PER_YEAR[tipo_periodo]
    poy = out["periodo"].map(lambda p: period_of_year(p, tipo_periodo))
    out["periodo_sin"] = np.sin(2 * np.pi * poy / ppy)
    out["periodo_cos"] = np.cos(2 * np.pi * poy / ppy)

    return out.sort_values([ID, "periodo"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Núcleo de modelagem (generalização de fit_mensal / ajuste_modelos_mensal.py)
# ---------------------------------------------------------------------------

def haversine_matrix(coords_a, coords_b):
    a = np.radians(np.atleast_2d(np.asarray(coords_a, float)))
    b = np.radians(np.atleast_2d(np.asarray(coords_b, float)))
    lon1, lat1 = a[:, 0][:, None], a[:, 1][:, None]
    lon2, lat2 = b[:, 0][None, :], b[:, 1][None, :]
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    h = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return EARTH_KM * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))


# ---------------------------------------------------------------------------
# Features derivadas pós-agregação: calculadas sobre o painel JÁ agregado
# pra periodicidade alvo (df_period) — por isso funcionam igual pra
# mês/trimestre/semestre/ano sem precisar de regra de agregação própria,
# ao contrário das antigas interações *_x_tempo/*_x_mes_sin/cos da SQL
# (removidas de pipeline_modelagem.py): aquelas só existiam em mês bruto e
# nunca sobreviviam ao aggregate_period, em nenhuma periodicidade — 23
# colunas mortas que nenhum modelo via.
# ---------------------------------------------------------------------------

_INTERACAO_SAZONAL_VARS = ("temp", "prec", "dias_calor", "dias_chuva")
_LAG_CLIMATICO_VARS = ("temp", "prec")
_QUADRATICO_VARS = ("temp", "prec")
_LOG_VARS = {"populacao": "log_pop", "dens_pop": "log_dens_pop", "pib": "log_pib"}


def _add_interacoes_sazonais(df):
    """Clima × sazonalidade (periodo_sin/periodo_cos) — dá aos modelos
    lineares (OLS/GWR/GTWR) o sinal "o efeito da temperatura muda com a
    estação", que só árvores (XGBoost) capturavam implicitamente até agora.

    DESATIVADA por pedido explícito do usuário (revertida, não chamada mais
    em `_add_engineered_features` — função preservada aqui, não removida):
    dar a OLS/GWR uma forma explícita de imitar modulação temporal reduzia
    a vantagem relativa do GTWR sobre os modelos lineares mais simples
    ("quero não trivializar o GTWR"), e o GTWR passou a perder pra eles em
    várias combinações de animal/cadência depois que essas interações (e o
    lag espacial `inc_viz`) entraram no conjunto de candidatas."""
    for var in _INTERACAO_SAZONAL_VARS:
        if var in df.columns:
            df[f"{var}_x_sin"] = df[var] * df["periodo_sin"]
            df[f"{var}_x_cos"] = df[var] * df["periodo_cos"]
    return df


def _add_lag_climatico(df):
    """Clima do período anterior — resposta biológica a clima costuma ter
    atraso (chuva favorece ocorrências semanas/meses depois, não no mesmo
    período)."""
    df = df.sort_values([ID, "periodo"])
    for var in _LAG_CLIMATICO_VARS:
        if var in df.columns:
            df[f"{var}_l1"] = df.groupby(ID)[var].shift(1)
    return df


def _add_termos_quadraticos(df):
    """Termo quadrático de clima — hipótese de janela ótima (muito frio OU
    muito calor reduzem atividade de artrópodes; a relação não é monotônica,
    então um termo linear sozinho não capturaria isso)."""
    for var in _QUADRATICO_VARS:
        if var in df.columns:
            df[f"{var}2"] = df[var] ** 2
    return df


def _add_log_socioeconomicas(df):
    """Log das variáveis socioeconômicas mais assimétricas — mantém a
    versão original também (não substitui): deixa o Lasso escolher qual das
    duas é mais linear com o alvo em vez de decidir isso de antemão."""
    for var, novo_nome in _LOG_VARS.items():
        if var in df.columns:
            df[novo_nome] = np.log1p(df[var].clip(lower=0))
    return df


def _add_lag_espacial(df, target, k=5):
    """Média do alvo nos `k` municípios geograficamente mais próximos, no
    MESMO período da linha (contemporânea — é uma covariável pra prever
    `y_next`, no mesmo nível temporal das demais features da linha, não
    informação do futuro). Dá aos modelos lineares um sinal direto de
    contágio/clustering espacial — hoje só GWR/GTWR veem vizinhança, e só
    via o próprio ajuste local, nunca como covariável explícita que o OLS
    também possa usar."""
    muni = df.drop_duplicates(ID)[[ID, "latitude", "longitude"]].reset_index(drop=True)
    if len(muni) <= k:
        df["inc_viz"] = np.nan
        return df

    coords = muni[["longitude", "latitude"]].to_numpy()
    dist = haversine_matrix(coords, coords)
    np.fill_diagonal(dist, np.inf)
    nn_idx = np.argsort(dist, axis=1)[:, :k]

    ids = muni[ID].to_numpy()
    pares = pd.DataFrame({
        ID: np.repeat(ids, k),
        "viz_id": ids[nn_idx.ravel()],
    })

    valores = df[[ID, "periodo", target]].rename(columns={ID: "viz_id", target: "viz_valor"})
    tmp = pares.merge(valores, on="viz_id")
    media_viz = tmp.groupby([ID, "periodo"])["viz_valor"].mean().reset_index(name="inc_viz")

    return df.merge(media_viz, on=[ID, "periodo"], how="left")


def _add_lag_target(df, target):
    """Incidência do período ANTERIOR — observada, não prevista: simples
    shift do próprio alvo da linha (`y_t`), não de `y_next`. Pedido
    explícito do usuário: dar aos modelos lineares um termo autorregressivo
    com 1 lag adicional além do já existente `incidencia_100k` (que é o
    valor do período ATUAL da linha, usado pra prever o seguinte). Nome de
    saída fixo em "inc_l1" (curto, no mesmo padrão de "inc_viz") em vez de
    `f"{target}_l1"` — assume target="incidencia_100k", único valor usado
    por este pipeline hoje."""
    df = df.sort_values([ID, "periodo"])
    df["inc_l1"] = df.groupby(ID)[target].shift(1)
    return df


def _add_engineered_features(df_period, target, k_viz=5):
    df = df_period.copy()
    # _add_interacoes_sazonais fica de fora de propósito (ver docstring)
    df = _add_lag_climatico(df)
    df = _add_termos_quadraticos(df)
    df = _add_log_socioeconomicas(df)
    df = _add_lag_espacial(df, target, k=k_viz)
    df = _add_lag_target(df, target)
    return df


def _split_train(model_df, inicio_treino, fim_treino, inicio_teste, fim_teste):
    model_df["periodo_int"] = model_df["periodo"].astype(int)
    train_df = model_df.loc[model_df["periodo_int"].between(inicio_treino, fim_treino)].copy()
    test_df = model_df.loc[model_df["periodo_int"].between(inicio_teste, fim_teste)].copy()

    if train_df.empty or test_df.empty:
        raise ValueError(
            f"Split inválido: n_train={len(train_df)}, n_test={len(test_df)}. "
            "Verifique se existem observações nesses períodos."
        )

    train_periods = sorted(train_df["periodo_int"].unique())
    test_periods = sorted(test_df["periodo_int"].unique())
    return train_df, test_df, len(train_df), len(test_df), train_periods, test_periods


def _build_test_geo(df_pred, pred_col, last_period):
    cols = ["id_municipio", "periodo", "total_ocorrencias", "y_t", "y_next", pred_col]
    out = (
        df_pred.loc[df_pred["periodo"] == last_period, cols]
        .rename(columns={"y_t": "observado", pred_col: "predito"})
        .copy()
    )
    out[["observado", "predito", "total_ocorrencias"]] = (
        out[["observado", "predito", "total_ocorrencias"]].astype(float)
    )
    out["residuo"] = out["y_next"].astype(float) - out["predito"]
    return out.drop(columns=["y_next"]).set_index("id_municipio").sort_index()


def _build_forecast_geo(forecast_df, yhat, metodo, forecast_period):
    return (
        pd.DataFrame({
            "id_municipio": forecast_df["id_municipio"].values,
            "periodo": forecast_period,
            "predito": np.maximum(0, np.asarray(yhat, dtype=float)),
            "total_ocorrencias": forecast_df["total_ocorrencias"].astype(float).values,
            "metodo": metodo,
        })
        .set_index("id_municipio")
        .sort_index()
    )


def fit_periodo(
    df_mensal,
    tipo_periodo: str,
    target: str,
    forecast_period: int,
    drop_columns: list = None,
    inicio_treino: int = None,
    fim_treino: int = None,
    inicio_teste: int = None,
    fim_teste: int = None,
    top_k: int = 20,
    rolling_window_periods: int = 6,
    rolling_min_train_periods: int = 3,
):
    """
    Versão unificada de `fit_mensal` (ajuste_modelos_mensal.py): mesma lógica
    de seleção de variáveis, OLS, GWR, GWR-Adaptativo, GTWR, Índice de Moran e
    métricas, parametrizada pela periodicidade (`tipo_periodo` em
    "mes"/"trimestre"/"semestre"/"ano") em vez de fixada em meses.

    `df_mensal` é o painel MENSAL cru (mesma query já usada pela versão
    mensal); a agregação para a periodicidade alvo acontece aqui dentro via
    `aggregate_period`.
    """
    if tipo_periodo not in PERIODS_PER_YEAR:
        raise ValueError(f"tipo_periodo inválido: {tipo_periodo!r}")

    df_period = aggregate_period(df_mensal, tipo_periodo)
    df_period = _add_engineered_features(df_period, target)

    df_model = df_period.copy()
    df_model[target] = (
        pd.to_numeric(df_model[target], errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )
    df_model["periodo"] = pd.to_numeric(df_model["periodo"], errors="coerce").astype("Int64")
    df_model = df_model.dropna(subset=["id_municipio", "periodo"]).sort_values(["id_municipio", "periodo"])

    df_model["y_next"] = df_model.groupby("id_municipio")[target].shift(-1)
    df_model["y_t"] = df_model[target]

    model_df = df_model.dropna(subset=["y_next"]).copy()
    candidate_features = (
        model_df
        .drop(columns=drop_columns or [], errors="ignore")
        .select_dtypes(include=[np.number])
        .columns.tolist()
    )
    # "id_municipio" é identificador (código IBGE), não covariável — entrava
    # como candidata numérica por engano (bug: nenhum filtro excluía).
    candidate_features = [
        c for c in candidate_features
        if c not in ("periodo", "periodo_fim_anomes", "id_municipio")
    ]
    print(f"[{tipo_periodo}] N features candidatas:", len(candidate_features))

    periods_available = sorted(int(p) for p in model_df["periodo"].unique())
    if inicio_treino is None or fim_treino is None or inicio_teste is None or fim_teste is None:
        raise ValueError("Informe inicio_treino/fim_treino/inicio_teste/fim_teste.")

    train_df, test_df, n_train, n_test, train_periods, test_periods = _split_train(
        model_df, inicio_treino, fim_treino, inicio_teste, fim_teste
    )
    test_last_period = max(test_periods)

    forecast_df = df_model.loc[df_model["periodo"].astype(int) == forecast_period].copy()
    if forecast_df.empty:
        raise ValueError(f"Nenhuma linha encontrada para forecast_period={forecast_period}.")

    print("\n" + "=" * 140)
    print(f"SPLIT FIXO [{tipo_periodo}]")
    print("=" * 140)
    print(f"Treino : {min(train_periods)} → {max(train_periods)}  (n_periodos={len(train_periods)})")
    print(f"Teste  : {min(test_periods)} → {max(test_periods)}  (n_periodos={len(test_periods)})")

    # ── Baselines ──────────────────────────────────────────────────────────
    y_true = test_df["y_next"].astype(float).values
    yhat_zero = np.zeros_like(y_true)
    yhat_persist = test_df["y_t"].astype(float).values
    mun_mean = train_df.groupby("id_municipio")["y_t"].mean()
    yhat_hist = test_df["id_municipio"].map(mun_mean).fillna(mun_mean.mean()).astype(float).values

    # ── Seleção rolling-window + OLS global (Lasso temporal + stepwise AIC,
    #    mesmo método de ajuste_modelos_mensal.py / utils_modelagem.py) ──────
    train_periods_sorted = sorted(int(p) for p in train_periods)
    if rolling_window_periods < rolling_min_train_periods:
        raise ValueError("rolling_window_periods deve ser >= rolling_min_train_periods.")

    rolling_records = []
    feature_frequency = {}
    for pos in range(rolling_min_train_periods, len(train_periods_sorted)):
        validation_period = train_periods_sorted[pos]
        window_start = max(0, pos - rolling_window_periods)
        fit_periods = train_periods_sorted[window_start:pos]

        fold_train = train_df.loc[train_df["periodo"].astype(int).isin(fit_periods)].copy()
        fold_valid = train_df.loc[train_df["periodo"].astype(int) == validation_period].copy()
        if fold_train.empty or fold_valid.empty:
            continue

        fold_sel = fit_predict_lasso_base_models(
            fold_train, fold_valid, candidate_features,
            target_col="y_next", top_k=top_k, verbose=False,
        )
        for feature in fold_sel["selected_features"]:
            feature_frequency[feature] = feature_frequency.get(feature, 0) + 1

        rolling_records.append({
            "periodo_validacao": validation_period,
            "periodos_treino": fit_periods,
            "n_train": len(fold_train),
            "n_valid": len(fold_valid),
            "mse_validacao": float(np.mean(
                (fold_valid["y_next"].astype(float).values - fold_sel["yhat_ols"]) ** 2
            )),
            "n_features": len(fold_sel["selected_features"]),
        })

    if not rolling_records:
        raise ValueError(
            "Não há janelas temporais suficientes para a seleção rolling. "
            "Reduza rolling_min_train_periods ou amplie o período de treino."
        )

    n_windows = len(rolling_records)
    top_k_features = [
        feature for feature, _ in sorted(
            feature_frequency.items(), key=lambda item: (-item[1], item[0])
        )[:top_k]
    ]
    selected_features = top_k_features
    if not selected_features:
        raise ValueError("A seleção rolling não reteve nenhuma variável.")

    sel = fit_predict_lasso_base_models(
        train_df, test_df, selected_features,
        target_col="y_next", top_k=len(selected_features),
    )
    yhat_ols = sel["yhat_ols"]
    selected_features = sel["selected_features"]
    rolling_selection_df = pd.DataFrame(rolling_records)

    # ── Baseline XGBoost: mesmas selected_features e mesma imputação
    # (reaproveita sel["imputer"], já ajustado em train_df[selected_features])
    # usadas pelo OLS/GWR/GTWR — comparação justa, sem busca de
    # hiperparâmetros própria (não é um "método" novo, é só mais um baseline
    # de referência, ao lado de zero/persistência/média municipal) ─────────
    X_train_xgb = sel["imputer"].transform(train_df[selected_features])
    X_test_xgb = sel["imputer"].transform(test_df[selected_features])
    xgb_model = XGBRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8, random_state=42, n_jobs=-1,
    )
    xgb_model.fit(X_train_xgb, train_df["y_next"].astype(float).values)
    yhat_xgb = np.maximum(0, xgb_model.predict(X_test_xgb).astype(float))

    # ── Estabilidade das variáveis: com que frequência cada candidata foi
    # selecionada entre as janelas rolling, e se sobreviveu tanto ao corte
    # por top_k quanto ao reajuste final (Lasso + stepwise AIC) ────────────
    feature_stability = (
        pd.DataFrame([
            {"feature": f, "n_janelas_selecionada": c, "n_janelas_total": n_windows,
             "frequencia": c / n_windows if n_windows else 0.0}
            for f, c in feature_frequency.items()
        ])
        .sort_values(["frequencia", "feature"], ascending=[False, True])
        .reset_index(drop=True)
    )
    feature_stability["no_top_k"] = feature_stability["feature"].isin(top_k_features)
    feature_stability["no_modelo_final"] = feature_stability["feature"].isin(selected_features)

    # Versão serializável (dict) da estabilidade, uma entrada por variável do
    # modelo final — é a mesma seleção para os 4 modelos "reais" (a escolha
    # de variáveis acontece uma vez só, antes de ajustar OLS/GWR/GWR-
    # Adaptativo/GTWR), então essa estrutura é compartilhada entre eles.
    estabilidade_variaveis_json = {
        row["feature"]: {
            "n_janelas_selecionada": int(row["n_janelas_selecionada"]),
            "n_janelas_total": int(row["n_janelas_total"]),
            "frequencia": float(row["frequencia"]),
        }
        for _, row in feature_stability.loc[feature_stability["no_modelo_final"]].iterrows()
    }

    print(f"\nJanelas válidas: {len(rolling_selection_df)}")
    print(f"Selecionadas por estabilidade (top {top_k}): {selected_features}")
    print("\nEstabilidade das variáveis selecionadas no modelo final (freq. entre janelas rolling):")
    print(
        feature_stability.loc[feature_stability["no_modelo_final"],
                               ["feature", "n_janelas_selecionada", "n_janelas_total", "frequencia"]]
        .round(3).to_string(index=False)
    )
    baixa_estabilidade = feature_stability.loc[
        feature_stability["no_modelo_final"] & (feature_stability["frequencia"] < 0.5)
    ]
    if not baixa_estabilidade.empty:
        print(
            f"[!] {len(baixa_estabilidade)} variável(is) no modelo final foram selecionadas em "
            f"menos de 50% das janelas rolling — tratar com cautela: "
            f"{baixa_estabilidade['feature'].tolist()}"
        )

    X_fc_raw = forecast_df[selected_features].replace([np.inf, -np.inf], np.nan)
    X_fc_ols = pd.DataFrame(sel["imputer"].transform(X_fc_raw), columns=selected_features, index=forecast_df.index)
    X_fc_ols = sm.add_constant(X_fc_ols, has_constant="add")
    yhat_ols_forecast = np.maximum(0, sel["ols"].predict(X_fc_ols).astype(float))

    # ── Modelos espaciais (GWR fixo, GWR adaptativo, GTWR) ──────────────────
    coords_fc = forecast_df[["longitude", "latitude"]].astype(float).values
    # GTWR normaliza dt pra unidades de período (ver period_months em
    # fit_predict_gtwr/gtwr.py) — times_fc precisa da MESMA normalização
    # antes de alimentar gtwr_model.predict(), senão o dt do forecast fica
    # numa escala diferente da usada no ajuste.
    times_fc = anomes_to_month_index(forecast_df["periodo_fim_anomes"]) / PERIOD_MONTHS[tipo_periodo]

    gwr_kwargs = dict(
        selected_features=selected_features, coord_cols=("longitude", "latitude"),
        bw_max_iter=15, verbose=True,
    )

    gwr_out = fit_predict_gwr(train_df=train_df, test_df=test_df, kernel="gaussian", search="grid", **gwr_kwargs)
    yhat_gwr = np.asarray(gwr_out["yhat"], dtype=float)
    yhat_gwr_forecast = np.maximum(0, gwr_out["gwr_model"].predict(
        gwr_out["imputer"].transform(X_fc_raw), coords_fc
    ))
    print(f"\nBandwidth GWR: {gwr_out['bandwidth_km']:.4f} km | LOOCV-MSE: {gwr_out['loocv_mse']:.6f}")

    gwra_out = fit_predict_gwr(
        train_df=train_df, test_df=test_df, kernel="gaussian", adaptive=True, bw_tol=1.0,
        **{k: v for k, v in gwr_kwargs.items() if k != "bw_tol"},
    )
    yhat_gwra = np.asarray(gwra_out["yhat"], dtype=float)
    yhat_gwra_forecast = np.maximum(0, gwra_out["gwr_model"].predict(
        gwra_out["imputer"].transform(X_fc_raw), coords_fc
    ))
    bandwidth_s = gwra_out.get("bandwidth_k")

    gtwr_kwargs = {
        "selected_features": selected_features, "coord_cols": ("longitude", "latitude"),
        "time_col": "periodo_fim_anomes", "period_months": PERIOD_MONTHS[tipo_periodo],
        "verbose": False,
    }
    # GTWR ajusta seu próprio bandwidth espacial (k_s) e tau — deixou de
    # herdar o k do GWR-Adaptativo (fixed_bw_s) de forma rígida. Em vez
    # disso, usa esse mesmo k como CENTRO de uma janela de busca (±60%): o
    # range fixo anterior (8-65 vizinhos) era muito menor que o ótimo que o
    # GWR-Adaptativo costuma encontrar para estes dados (~150-200), o que
    # empurrava a busca de k_s para a borda superior do range (overfitting
    # por vizinhança pequena demais). A busca usa apenas os períodos mais
    # recentes de treino (todos os municípios mantidos) para ficar rápida —
    # ver search_max_periods em fit_predict_gtwr / gtwr.py.
    k_s_centro = max(4, int(round(bandwidth_s))) if bandwidth_s else 40
    gtwrgauss_out = fit_predict_gtwr(
        train_df=train_df, test_df=test_df,
        search_method="golden", search_max_periods=12,
        bw_min=max(4, int(k_s_centro * 0.4)), bw_max=max(int(k_s_centro * 1.6), int(k_s_centro * 0.4) + 8),
        **gtwr_kwargs,
    )
    yhat_gtwrgauss = np.asarray(gtwrgauss_out["yhat"], dtype=float)
    yhat_gtwrgauss_forecast = np.maximum(0, gtwrgauss_out["gtwr_model"].predict(
        gtwrgauss_out["imputer"].transform(X_fc_raw), coords_fc, times_fc
    ))

    # ── Pesos das variáveis: coeficiente único (OLS) ou quantis entre
    # municípios/observações (modelos locais — GWR, GWR-Adaptativo, GTWR,
    # cujos coeficientes variam no espaço e, no caso do GTWR, também no
    # tempo). Mesma convenção ("tipo": "global"/"quantis_locais") já usada
    # na tentativa de unificação anterior (ajuste_modelos.py, _coef_summary),
    # mantida por familiaridade. ──────────────────────────────────────────
    def _pesos_locais(coeficientes_por_observacao, labels):
        """`coeficientes_por_observacao`: array (n, len(labels)+1), coluna 0
        = intercepto — uma linha por município (GWR) ou por observação
        município×período (GTWR)."""
        nomes = ["intercepto", *labels]
        quantis = np.quantile(coeficientes_por_observacao, [0.25, 0.5, 0.75], axis=0)
        return {
            "tipo": "quantis_locais",
            "n_observacoes": int(coeficientes_por_observacao.shape[0]),
            "coeficientes": {
                nome: {"q1": float(q[0]), "mediana": float(q[1]), "q3": float(q[2])}
                for nome, q in zip(nomes, quantis.T)
            },
        }

    pesos_variaveis = {
        "ols": {
            "tipo": "global",
            "coeficientes": {
                ("intercepto" if str(k) == "const" else str(k)): float(v)
                for k, v in sel["ols"].params.items()
            },
        },
        "gwr": _pesos_locais(gwr_out["gwr_model"].betas_by_city_, selected_features),
        "gwr_adaptativo": _pesos_locais(gwra_out["gwr_model"].betas_by_city_, selected_features),
        "gtwr": _pesos_locais(gtwrgauss_out["gtwr_model"].coef_, selected_features),
    }

    # ── Índice de Moran dos resíduos ─────────────────────────────────────────
    bw_s = float(gwr_out["bandwidth_km"])

    def gaussian_weights(D, bw):
        W = np.exp(-0.5 * (D / bw) ** 2)
        np.fill_diagonal(W, 0.0)
        return W

    def moran_por_periodo(residuals, nome_modelo):
        base = test_df[["id_municipio", "periodo", "latitude", "longitude"]].copy()
        base["periodo"] = base["periodo"].astype(int)
        base["residual"] = np.asarray(residuals, float)

        registros = []
        for periodo, g in base.groupby("periodo"):
            if len(g) < 3:
                continue
            coords_m = g[["longitude", "latitude"]].values
            resid_m = g["residual"].values
            D = haversine_matrix(coords_m, coords_m)
            W = gaussian_weights(D, bw_s)
            rs = W.sum(axis=1, keepdims=True)
            rs[rs == 0] = 1.0
            W = W / rs
            W[np.isnan(W)] = 0.0
            w = full2W(W)
            w.transform = "R"
            mi = Moran(resid_m, w)
            registros.append({"modelo": nome_modelo, "periodo": int(periodo), "moran_I": mi.I, "p_sim": mi.p_sim})
        return pd.DataFrame(registros)

    moran_dfs = [
        moran_por_periodo(y_true - yhat_ols, "OLS"),
        moran_por_periodo(y_true - yhat_gwr, "GWR"),
        moran_por_periodo(y_true - yhat_gwra, "GWR_ADAPTATIVO"),
        moran_por_periodo(y_true - yhat_gtwrgauss, "GTWR"),
    ]
    moran_por_periodo_df = pd.concat(moran_dfs, ignore_index=True)
    moran_resumo = (
        moran_por_periodo_df.groupby("modelo")
        .agg(moran_I_medio=("moran_I", "mean"), p_sim_medio=("p_sim", "mean"),
             meses_signif=("p_sim", lambda s: int((s < 0.05).sum())), n_meses=("p_sim", "size"))
        .reset_index()
    )

    # ── Métricas ──────────────────────────────────────────────────────────
    test_period_label = f"{min(test_periods)}-{max(test_periods)}"
    modelos = [
        ("Baseline zero", yhat_zero, 0),
        ("Baseline persistência", yhat_persist, 0),
        ("Baseline média municipal", yhat_hist, 0),
        ("Baseline XGBoost", yhat_xgb, len(selected_features)),
        ("OLS Global", yhat_ols, len(selected_features)),
        ("GWR (Gaussiano)", yhat_gwr, len(selected_features)),
        ("GWR-Adaptativo", yhat_gwra, len(selected_features)),
        ("GTWR - Gaussiano", yhat_gtwrgauss, len(selected_features)),
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
    print(f"RESULTADO COMPARATIVO GERAL [{tipo_periodo}]")
    print("=" * 140)
    print(df_eval.round(4).to_string(index=False))

    # ── Descrição completa por modelo (inclui baselines): métricas, tipo,
    # bandwidths (quando aplicável) e pesos das variáveis (quando aplicável)
    # — é essa estrutura que persist_results_periodo grava por inteiro, uma
    # linha por método, para viabilizar uma tabela comparativa com
    # baselines sem precisar recalcular nada a partir do zero. ────────────
    METODO_KEY = {
        "Baseline zero": "baseline_zero",
        "Baseline persistência": "baseline_persistencia",
        "Baseline média municipal": "baseline_media_municipal",
        "Baseline XGBoost": "baseline_xgboost",
        "OLS Global": "ols",
        "GWR (Gaussiano)": "gwr",
        "GWR-Adaptativo": "gwr_adaptativo",
        "GTWR - Gaussiano": "gtwr",
    }
    modelos_detalhados = []
    for _, linha in df_eval.iterrows():
        metodo_key = METODO_KEY[linha["modelo"]]
        entry = {
            "metodo": metodo_key,
            "nome": linha["modelo"],
            "tipo": "baseline" if metodo_key.startswith("baseline") else ("global" if metodo_key == "ols" else "local"),
            "n_features": int(linha["n_features"]),
            "mse": float(linha["MSE"]),
            "rmse": float(linha["RMSE"]),
            "mae": float(linha["MAE"]),
            "r2": float(linha["R2"]),
            "gain_vs_media_municipal": float(linha["gain_vs_media_municipal"]),
        }
        if metodo_key == "gwr":
            entry["bandwidth_km"] = float(gwr_out["bandwidth_km"])
        elif metodo_key == "gwr_adaptativo":
            entry["bandwidth_k"] = int(bandwidth_s) if bandwidth_s is not None else None
        elif metodo_key == "gtwr":
            entry["bandwidth_s"] = gtwrgauss_out.get("bw_s")
            entry["tau"] = gtwrgauss_out.get("tau")
        if metodo_key in pesos_variaveis:
            entry["pesos"] = pesos_variaveis[metodo_key]
            entry["estabilidade_variaveis"] = estabilidade_variaveis_json
        modelos_detalhados.append(entry)

    # ── Saídas para mapas ─────────────────────────────────────────────────
    df_pred = test_df[["id_municipio", "periodo", "total_ocorrencias", "y_t", "y_next"]].copy()
    df_pred["periodo"] = df_pred["periodo"].astype(int)
    for col, yhat in [
        ("pred_zero", yhat_zero), ("pred_persistencia", yhat_persist), ("pred_media_municipal", yhat_hist),
        ("pred_ols", yhat_ols), ("pred_gwr", yhat_gwr), ("pred_gwr_adaptativo", yhat_gwra),
        ("pred_gtwr", yhat_gtwrgauss),
    ]:
        df_pred[col] = yhat
        if col.startswith(("pred_ols", "pred_gwr", "pred_gtwr")):
            df_pred[col.replace("pred_", "erro_")] = df_pred["y_next"] - yhat

    return {
        "meta": {
            "tipo_periodo": tipo_periodo,
            "train_periods": train_periods,
            "test_periods": test_periods,
            "test_last_period": test_last_period,
            "forecast_period": forecast_period,
            "n_train": n_train,
            "n_test": n_test,
            "selected_features": selected_features,
            "rolling_window_periods": rolling_window_periods,
            "rolling_min_train_periods": rolling_min_train_periods,
            "gwr_bandwidth_km": gwr_out["bandwidth_km"],
        },
        "metricas": df_eval,
        "modelos_detalhados": modelos_detalhados,
        "pesos_variaveis": pesos_variaveis,
        "moran_resumo": moran_resumo,
        "selecao_rolling": rolling_selection_df,
        "estabilidade_variaveis": feature_stability,

        "geo_ols_teste": _build_test_geo(df_pred, "pred_ols", test_last_period),
        "geo_gwr_teste": _build_test_geo(df_pred, "pred_gwr", test_last_period),
        "geo_gwra_teste": _build_test_geo(df_pred, "pred_gwr_adaptativo", test_last_period),
        "geo_gtwr_teste": _build_test_geo(df_pred, "pred_gtwr", test_last_period),

        "geo_ols_forecast": _build_forecast_geo(forecast_df, yhat_ols_forecast, "ols_global", forecast_period),
        "geo_gwr_forecast": _build_forecast_geo(forecast_df, yhat_gwr_forecast, "gwr", forecast_period),
        "geo_gwra_forecast": _build_forecast_geo(forecast_df, yhat_gwra_forecast, "gwr_adaptativo", forecast_period),
        "geo_gtwr_forecast": _build_forecast_geo(forecast_df, yhat_gtwrgauss_forecast, "gtwr", forecast_period),

        "artifacts": {
            "gwra_bandwidth_k": bandwidth_s,
            "gtwr_bandwidth_s": gtwrgauss_out.get("bw_s"),
            "gtwr_tau": gtwrgauss_out.get("tau"),
        },
    }
