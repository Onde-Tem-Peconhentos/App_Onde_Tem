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


  