from sklearn.linear_model import LassoCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

import numpy as np
import statsmodels.api as sm
import pandas as pd
import warnings 
warnings.filterwarnings("ignore")


def feature_engineering(df_model):
    
    # =============================================================================
    # 2. Features temporais / lags
    # =============================================================================

    df_model["y_next"] = df_model.groupby("id_municipio")["total_ocorrencias"].shift(-1)
    df_model["y_t"]    = df_model["total_ocorrencias"]

    df_model["y_lag1"] = df_model.groupby("id_municipio")["total_ocorrencias"].shift(1)
    df_model["y_lag2"] = df_model.groupby("id_municipio")["total_ocorrencias"].shift(2)

    df_model["y_roll3"] = (
        df_model.groupby("id_municipio")["total_ocorrencias"]
        .transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    df_model["y_roll6"] = (
        df_model.groupby("id_municipio")["total_ocorrencias"]
        .transform(lambda s: s.rolling(6, min_periods=1).mean())
    )
    df_model["y_roll12"] = (
        df_model.groupby("id_municipio")["total_ocorrencias"]
        .transform(lambda s: s.rolling(12, min_periods=1).mean())
    )
    df_model["media_hist_municipio"] = (
        df_model.groupby("id_municipio")["total_ocorrencias"]
        .transform(lambda s: s.expanding().mean())
    )


    # =============================================================================
    # 3. Sazonalidade
    # =============================================================================

    df_model["mes"]     = (df_model["anomes"].astype(int) % 100).astype(int)
    df_model["mes_sin"] = np.sin(2 * np.pi * df_model["mes"] / 12)
    df_model["mes_cos"] = np.cos(2 * np.pi * df_model["mes"] / 12)
    
    return df_model



def calc_metrics(y_true, y_pred, modelo, test_period, n_train, n_test, n_features):
        """
        Calcula métricas de avaliação para um modelo específico, dado os valores verdadeiros e previstos.
        Parametros:
        - y_true: array-like, valores reais do target. 
        - y_pred: array-like, valores previstos pelo modelo.
        - modelo: str, nome do modelo (ex: "Lasso + OLS",
            "GWR", "Baseline média municipal", etc.)
        - test_period: str, descrição do período de teste (ex: "2025-01 a 2025-12").
        - n_train: int, número de observações no conjunto de treino.
        - n_test: int, número de observações no conjunto de teste.
        - n_features: int, número de features usadas no modelo (0 para baselines).
            Retorna:
        - dict com as métricas calculadas e informações do modelo.
        """
        mse = mean_squared_error(y_true, y_pred)
        return {
            "test_period":           test_period,
            "modelo":                modelo,
            "target_previsto":       "total_ocorrencias_mes_seguinte",
            "n_train":               n_train,
            "n_test":                n_test,
            "n_features":            n_features,
            "MSE":                   mse,
            "RMSE":                  np.sqrt(mse),
            "MAE":                   mean_absolute_error(y_true, y_pred),
            "R2":                    r2_score(y_true, y_pred),
        }


    # =============================================================================
    # 6B. Lasso + OLS
    # =============================================================================

from sklearn.pipeline import Pipeline
from sklearn.linear_model import LassoCV

def fit_predict_lasso_ols(train_df, test_df, candidate_features, top_k=15):
    """
    LassoCV para seleção de variáveis + OLS robusto (HC3).
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

    # --- OLS robusto (HC3) ---
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

    ols_model = sm.OLS(y_train, X_train_ols).fit(cov_type="HC3")
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