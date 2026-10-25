from sklearn.linear_model import LassoCV
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from statsmodels.stats.outliers_influence import variance_inflation_factor

import numpy as np
import statsmodels.api as sm
import pandas as pd
import warnings 
warnings.filterwarnings("ignore")


import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def feature_engineering(df_model, target: str = "incidencia_100k"):
    
    # =============================================================================
    # 2. Features temporais / lags
    # =============================================================================

    df_model["y_next"] = df_model.groupby("id_municipio")[target].shift(-1)
    df_model["y_t"]    = df_model[target]

    # df_model["y_lag1"] = df_model.groupby("id_municipio")[target].shift(1)
    # df_model["y_lag2"] = df_model.groupby("id_municipio")[target].shift(2)

    # df_model["y_roll3"] = (
    #     df_model.groupby("id_municipio")[target]
    #     .transform(lambda s: s.rolling(3, min_periods=1).mean())
    # )
    # df_model["y_roll6"] = (
    #     df_model.groupby("id_municipio")[target]
    #     .transform(lambda s: s.rolling(6, min_periods=1).mean())
    # )
    # df_model["y_roll12"] = (
    #     df_model.groupby("id_municipio")[target]
    #     .transform(lambda s: s.rolling(12, min_periods=1).mean())
    # )
    # df_model["media_hist_municipio"] = (
    #     df_model.groupby("id_municipio")[target]
    #     .transform(lambda s: s.expanding().mean())
    # )


    # =============================================================================
    # 3. Sazonalidade
    # =============================================================================

    df_model["mes"]     = (df_model["anomes"].astype(int) % 100).astype(int)
    df_model["mes_sin"] = np.sin(2 * np.pi * df_model["mes"] / 12)
    df_model["mes_cos"] = np.cos(2 * np.pi * df_model["mes"] / 12)
    df_model.drop(columns=["mes"], inplace=True)
    
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

def fit_predict_lasso_base_models(
    train_df,
    test_df,
    candidate_features,
    top_k=15,
    target_col="y_next",
    lasso_cv=5,
    improvement_tolerance=1e-8,
    verbose=False,
):
    """
    Seleção de variáveis realizada exclusivamente no conjunto de treino:

    1. LassoCV:
       - mantém apenas features cujo coeficiente seja diferente de zero.

    2. Stepwise bidirecional por AIC:
       - Forward: adiciona a variável que mais reduz o AIC;
       - Backward: após cada adição, remove alguma variável se isso reduzir
         ainda mais o AIC;
       - mantém no máximo top_k features.

    3. O teste é usado somente para avaliação final do modelo selecionado.

    Retorna métricas, modelos, features removidas e histórico do stepwise.
    """

    # =========================================================================
    # 1. Validação e preparação
    # =========================================================================

    if target_col not in train_df.columns:
        raise ValueError(
            f"A coluna target '{target_col}' não existe no train_df."
        )

    if target_col not in test_df.columns:
        raise ValueError(
            f"A coluna target '{target_col}' não existe no test_df."
        )

    if top_k < 1:
        raise ValueError("top_k deve ser maior ou igual a 1.")

    candidate_features = [
        col
        for col in candidate_features
        if col in train_df.columns
        and col in test_df.columns
        and col != target_col
    ]

    if not candidate_features:
        raise ValueError(
            "Nenhuma feature candidata foi encontrada simultaneamente "
            "em train_df e test_df."
        )

    X_train_original = (
        train_df[candidate_features]
        .replace([np.inf, -np.inf], np.nan)
        .copy()
    )

    X_test_original = (
        test_df[candidate_features]
        .replace([np.inf, -np.inf], np.nan)
        .copy()
    )

    y_train = train_df[target_col].astype(float).to_numpy()
    y_test = test_df[target_col].astype(float).to_numpy()

    features_com_dados = [col for col in X_train_original.columns if X_train_original[col].notna().any()] 

    X_train_original = X_train_original[features_com_dados].copy()
    X_test_original = X_test_original[features_com_dados].copy()

    if X_train_original.empty:
        raise ValueError(
            "Todas as features candidatas estão completamente nulas no treino."
        )

    imputer_pre_selecao = SimpleImputer(strategy="median")
    X_train_imputado = pd.DataFrame(
        imputer_pre_selecao.fit_transform(X_train_original),
        columns=X_train_original.columns,
        index=X_train_original.index,
    )

    # =========================================================================
    # 2. LassoCV com dobras temporais internas
    # =========================================================================
    X_train_lasso = X_train_imputado.copy()
    lasso_cv_strategy = lasso_cv

    if "anomes" in train_df.columns:
        meses = train_df["anomes"].astype(int).to_numpy()
        meses_unicos = np.sort(np.unique(meses))
        temporal_folds = []
        for pos in range(1, len(meses_unicos)):
            idx_treino = np.flatnonzero(meses < meses_unicos[pos])
            idx_validacao = np.flatnonzero(meses == meses_unicos[pos])
            if len(idx_treino) > 0 and len(idx_validacao) > 0:
                temporal_folds.append((idx_treino, idx_validacao))

        if len(temporal_folds) >= 2:
            lasso_cv_strategy = temporal_folds[-lasso_cv:]
        elif verbose:
            print("Aviso: meses insuficientes para CV temporal; usando cv numérico.")

    pipeline_lasso = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        (
            "lasso",
            LassoCV(
                cv=lasso_cv_strategy,
                max_iter=100_000,
                tol=1e-3,
                n_jobs=-1,
                random_state=42,
            ),
        ),
    ])

    pipeline_lasso.fit(X_train_lasso, y_train)

    lasso = pipeline_lasso.named_steps["lasso"]

    coef_lasso = pd.Series(
        lasso.coef_,
        index=X_train_lasso.columns,
        dtype=float,
    )

    features_lasso = (
        coef_lasso[coef_lasso != 0]
        .sort_values(
            key=lambda serie: serie.abs(),
            ascending=False,
        )
        .index
        .tolist()
    )

    # Fallback se Lasso zerar todas as features.
    if not features_lasso:
        # Calcula a correlação de cada feature com o target para salvar a melhor
        correlacoes = X_train_lasso.apply(lambda col: np.abs(np.corrcoef(col, y_train)[0, 1]))
        melhor_feature = correlacoes.sort_values(ascending=False).index[0]
        features_lasso = [melhor_feature]
        if verbose:
            print(f"Aviso: Lasso zerou todas as features. Fallback para a feature com maior correlação: {melhor_feature}")

    # =========================================================================
    # 3. Stepwise bidirecional por AIC
    # =========================================================================

    imputer_stepwise = SimpleImputer(strategy="median")

    X_train_stepwise = pd.DataFrame(
        imputer_stepwise.fit_transform(
            X_train_original[features_lasso]
        ),
        columns=features_lasso,
        index=train_df.index,
    )

    def ajustar_ols(features):
        """
        Ajusta OLS usando somente as features recebidas.
        Aceita uma lista vazia para permitir comparação com o modelo nulo.
        """
        if features:
            X_modelo = sm.add_constant(
                X_train_stepwise[features],
                has_constant="add",
            )
        else:
            X_modelo = pd.DataFrame(
                {"const": np.ones(len(X_train_stepwise))},
                index=X_train_stepwise.index,
            )

        return sm.OLS(y_train, X_modelo).fit()

    # Modelo nulo: somente intercepto.
    modelo_atual = ajustar_ols([])
    aic_atual = modelo_atual.aic

    selected_features = []
    remaining_features = features_lasso.copy()
    historico_stepwise = []

    while (
        remaining_features
        and len(selected_features) < top_k
    ):

        # ---------------------------------------------------------------------
        # Forward: adiciona a variável que mais reduz o AIC.
        # ---------------------------------------------------------------------

        candidatos_adicao = []

        for feature in remaining_features:
            features_teste = selected_features + [feature]
            modelo_teste = ajustar_ols(features_teste)

            candidatos_adicao.append(
                {
                    "feature": feature,
                    "features": features_teste,
                    "modelo": modelo_teste,
                    "aic": modelo_teste.aic,
                }
            )

        melhor_adicao = min(
            candidatos_adicao,
            key=lambda item: item["aic"],
        )

        if melhor_adicao["aic"] >= aic_atual - improvement_tolerance:
            break

        aic_anterior = aic_atual
        feature_adicionada = melhor_adicao["feature"]

        selected_features.append(feature_adicionada)
        remaining_features.remove(feature_adicionada)

        modelo_atual = melhor_adicao["modelo"]
        aic_atual = melhor_adicao["aic"]

        historico_stepwise.append(
            {
                "etapa": len(historico_stepwise) + 1,
                "acao": "adicionar",
                "feature": feature_adicionada,
                "n_features": len(selected_features),
                "aic_anterior": aic_anterior,
                "aic_novo": aic_atual,
                "delta_aic": aic_anterior - aic_atual,
                "features_modelo": selected_features.copy(),
            }
        )

        # ---------------------------------------------------------------------
        # Backward: remove qualquer variável que reduza ainda mais o AIC.
        # ---------------------------------------------------------------------

        while len(selected_features) > 1:
            candidatos_remocao = []

            for feature in selected_features:
                features_teste = [
                    item
                    for item in selected_features
                    if item != feature
                ]

                modelo_teste = ajustar_ols(features_teste)

                candidatos_remocao.append(
                    {
                        "feature": feature,
                        "features": features_teste,
                        "modelo": modelo_teste,
                        "aic": modelo_teste.aic,
                    }
                )

            melhor_remocao = min(
                candidatos_remocao,
                key=lambda item: item["aic"],
            )

            if melhor_remocao["aic"] >= aic_atual - improvement_tolerance:
                break

            aic_anterior = aic_atual
            feature_removida = melhor_remocao["feature"]

            selected_features.remove(feature_removida)
            remaining_features.append(feature_removida)

            modelo_atual = melhor_remocao["modelo"]
            aic_atual = melhor_remocao["aic"]

            historico_stepwise.append(
                {
                    "etapa": len(historico_stepwise) + 1,
                    "acao": "remover",
                    "feature": feature_removida,
                    "n_features": len(selected_features),
                    "aic_anterior": aic_anterior,
                    "aic_novo": aic_atual,
                    "delta_aic": aic_anterior - aic_atual,
                    "features_modelo": selected_features.copy(),
                }
            )

    # Garante que o modelo final tenha pelo menos uma feature.
    if not selected_features:
        selected_features = [features_lasso[0]]

    # =========================================================================
    # 4. Modelo OLS final e avaliação no teste
    # =========================================================================

    imputer_final = SimpleImputer(strategy="median")

    X_train_final = pd.DataFrame(
        imputer_final.fit_transform(
            X_train_original[selected_features]
        ),
        columns=selected_features,
        index=train_df.index,
    )

    X_test_final = pd.DataFrame(
        imputer_final.transform(
            X_test_original[selected_features]
        ),
        columns=selected_features,
        index=test_df.index,
    )

    X_train_final_ols = sm.add_constant(
        X_train_final,
        has_constant="add",
    )

    X_test_final_ols = sm.add_constant(
        X_test_final,
        has_constant="add",
    )

    ols_final = sm.OLS(
        y_train,
        X_train_final_ols,
    ).fit()

    yhat_train = np.maximum(
        0,
        ols_final.predict(X_train_final_ols).astype(float),
    )

    yhat_test = np.maximum(
        0,
        ols_final.predict(X_test_final_ols).astype(float),
    )

    mse_train_final = float(
        mean_squared_error(y_train, yhat_train)
    )

    mse_test = float(
        mean_squared_error(y_test, yhat_test)
    )

    rmse_test = float(np.sqrt(mse_test))
    mae_test = float(mean_absolute_error(y_test, yhat_test))

    try:
        r2_test = float(r2_score(y_test, yhat_test))
    except ValueError:
        r2_test = np.nan

    # =========================================================================
    # 5. Tabelas de resultado e diagnóstico
    # =========================================================================

    df_lasso = (
        coef_lasso
        .rename("coef_lasso")
        .reset_index()
        .rename(columns={"index": "feature"})
    )

    df_lasso["coef_abs"] = df_lasso["coef_lasso"].abs()
    df_lasso["selecionada_lasso"] = df_lasso["coef_lasso"] != 0

    df_lasso = df_lasso.sort_values(
        "coef_abs",
        ascending=False,
    ).reset_index(drop=True)

    df_stepwise = pd.DataFrame(historico_stepwise)

    metricas = {
        "MSE_train": mse_train_final,
        "MSE_test": mse_test,
        "RMSE_test": rmse_test,
        "MAE_test": mae_test,
        "R2_test": r2_test,
    }

    if verbose:
        print("\n" + "=" * 100)
        print("SELEÇÃO: LASSO TEMPORAL → STEPWISE")
        print("=" * 100)
        print(f"\nFeatures candidatas iniciais: {len(candidate_features)}")
        print(f"Features não zeradas no Lasso: {len(features_lasso)}")
        print(f"Features finais no Stepwise: {len(selected_features)}")
        print("\nFeatures finais:")
        print(selected_features)
        print("\nMétricas finais:")
        print(f"MSE treino: {mse_train_final:.6f}")
        print(f"MSE teste:  {mse_test:.6f}")
        print(f"MAE teste:  {mae_test:.6f}")
        print(f"R² teste:   {r2_test:.6f}")

    return {
        # Modelo e predições
        "ols": ols_final,
        "betas_ols": ols_final.params.to_dict(),
        "imputer": imputer_final,
        "yhat_train": yhat_train,
        "yhat_ols": yhat_test,
        "yhat_test": yhat_test,

        # Features selecionadas
        "selected_features": selected_features,
        "best_features": selected_features,
        "n_features_final": len(selected_features),

        # Métricas
        "best_score": mse_test,
        "metricas": metricas,
        "mse_train": mse_train_final,
        "mse_test": mse_test,
        "mae_test": mae_test,
        "r2_test": r2_test,

        # Lasso
        "lasso": lasso,
        "coef_lasso": coef_lasso,
        "ordered_features": (
            coef_lasso
            .sort_values(key=lambda serie: serie.abs(), ascending=False)
        ),
        "lasso_nonzero": int((coef_lasso != 0).sum()),
        "features_lasso": features_lasso,
        "df_lasso": df_lasso,

        # Stepwise
        "df_steps": df_stepwise,
        "df_stepwise": df_stepwise,
    }