import math
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

def haversine_vector(coord, coords):
    """
    Calcula a distância em quilômetros (km) entre um ponto de referência e uma matriz de pontos.
    Utiliza a fórmula de Haversine para considerar a curvatura da Terra.

    Args:
        coord (array-like): Coordenada de referência [longitude, latitude].
        coords (np.ndarray): Matriz bidimensional de coordenadas locais, formato (n, 2) 
                             onde a coluna 0 é longitude e a coluna 1 é latitude.

    Returns:
        np.ndarray: Vetor 1D contendo as distâncias em km.
    """
    lon1, lat1 = np.radians(coord[0]), np.radians(coord[1])
    lon2 = np.radians(coords[:, 0])
    lat2 = np.radians(coords[:, 1])

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )
    c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
    return 6371.0088 * c


def gwr_kernel_weights(dist_km, bandwidth, kernel="gaussian"):
    """
    Gera pesos espaciais baseados na distância e em uma largura de banda (bandwidth).

    Args:
        dist_km (np.ndarray): Vetor de distâncias em km.
        bandwidth (float): Raio de influência (largura de banda) do kernel.
        kernel (str, opcional): Tipo de função kernel a ser utilizada. 
                                Opções: "gaussian" (padrão) ou "bisquare".

    Returns:
        np.ndarray: Vetor 1D de pesos espaciais calculados.
        
    Raises:
        ValueError: Se o kernel especificado não for suportado.
    """
    bandwidth = max(float(bandwidth), 1e-8)
    if kernel == "gaussian":
        return np.exp(-0.5 * (dist_km / bandwidth) ** 2)
    elif kernel == "bisquare":
        u = dist_km / bandwidth
        w = (1 - u ** 2) ** 2
        w[u >= 1] = 0.0
        return w
    else:
        raise ValueError(f"Kernel não suportado: {kernel}")


def add_intercept(X):
    """
    Adiciona uma coluna de 'uns' no início da matriz para atuar como intercepto do modelo.

    Args:
        X (array-like): Matriz de variáveis independentes (features) de formato (n, p).

    Returns:
        np.ndarray: Matriz de formato (n, p+1) com a coluna do intercepto inserida na posição 0.
    """
    return np.column_stack([np.ones(len(X)), X])


def weighted_ridge_beta(X, y, w, ridge=1e-6):
    """
    Calcula os coeficientes (betas) de uma Regressão Linear Ponderada localmente, 
    aplicando uma penalização Ridge para evitar problemas de multicolinearidade.

    Args:
        X (array-like): Matriz de features de formato (n, p).
        y (array-like): Vetor de variáveis dependentes (alvo) de formato (n,).
        w (array-like): Vetor de pesos de formato (n,).
        ridge (float, opcional): Fator de penalização Ridge. Padrão é 1e-6.

    Returns:
        np.ndarray: Vetor 1D com os coeficientes da regressão (incluindo intercepto se presente).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1, 1)
    w = np.asarray(w, dtype=float).reshape(-1)

    sw  = np.sqrt(w).reshape(-1, 1)
    Xw  = X * sw
    yw  = y * sw

    p = X.shape[1]
    ridge_mat = np.eye(p) * ridge
    ridge_mat[0, 0] = 0.0  # não penaliza intercepto

    beta = np.linalg.pinv(Xw.T @ Xw + ridge_mat) @ (Xw.T @ yw)
    return beta.reshape(-1)


class GeographicallyWeightedRegression:
    """
    Implementação de uma Regressão Geograficamente Ponderada (GWR) simplificada.
    Utiliza kernel espacial (Haversine) e suporta predição out-of-sample (fora da amostra) 
    bem como Leave-One-Out Cross Validation (LOOCV).

    Atributos:
        bandwidth (float): Largura de banda em quilômetros.
        kernel (str): Tipo de kernel espacial ("gaussian" ou "bisquare").
        ridge (float): Constante de penalização Ridge para estabilidade numérica.
        is_fitted_ (bool): Indica se o modelo já foi ajustado (fit) aos dados.
    """

    def __init__(self, bandwidth, kernel="gaussian", ridge=1e-6):
        self.bandwidth = float(bandwidth)
        self.kernel    = kernel
        self.ridge     = ridge
        self.is_fitted_ = False

    def fit(self, X, y, coords):
        """
        Ajusta o modelo GWR armazenando internamente as features, target e coordenadas de treino.

        Args:
            X (array-like): Matriz de features de treino.
            y (array-like): Vetor alvo de treino.
            coords (array-like): Coordenadas de treino.

        Returns:
            GeographicallyWeightedRegression: A própria instância do modelo ajustada.
        """
        self.X_      = add_intercept(np.asarray(X, dtype=float))
        self.y_      = np.asarray(y, dtype=float).reshape(-1)
        self.coords_ = np.asarray(coords, dtype=float)
        self.is_fitted_ = True
        return self

    def _local_beta(self, coord, loo_idx=None):
        """
        Calcula os coeficientes (betas) locais para uma única coordenada.

        Args:
            coord (array-like): Coordenada local para a qual se deseja calcular o modelo.
            loo_idx (int, opcional): Índice a ser ignorado (zerado no peso) durante o LOOCV.

        Returns:
            np.ndarray: Vetor de coeficientes (betas) locais.
        """
        d = haversine_vector(coord, self.coords_)
        w = gwr_kernel_weights(d, self.bandwidth, kernel=self.kernel)

        if loo_idx is not None:
            w[loo_idx] = 0.0

        mask = w > 1e-12
        if mask.sum() < self.X_.shape[1]:
            w    = np.maximum(w, 1e-8)
            mask = np.ones(len(w), dtype=bool)

        return weighted_ridge_beta(
            self.X_[mask], self.y_[mask], w[mask], ridge=self.ridge
        )

    def predict(self, X_new, coords_new):
        """
        Gera predições para novos dados a partir da estimação local.

        Args:
            X_new (array-like): Matriz de novas features.
            coords_new (array-like): Novas coordenadas correspondentes às linhas de X_new.

        Returns:
            np.ndarray: Vetor de valores preditos.
            
        Raises:
            ValueError: Se o modelo ainda não tiver sido ajustado via método `.fit()`.
        """
        if not self.is_fitted_:
            raise ValueError("Modelo não ajustado. Chame .fit() primeiro.")

        X_new      = add_intercept(np.asarray(X_new, dtype=float))
        coords_new = np.asarray(coords_new, dtype=float)

        preds = np.array([
            float(X_new[i] @ self._local_beta(coords_new[i]))
            for i in range(len(X_new))
        ])
        return preds

    def loocv_mse(self, X, y, coords):
        """
        Calcula o Erro Quadrático Médio (MSE) via Leave-One-Out Cross-Validation.
        
        Args:
            X (array-like): Matriz de features.
            y (array-like): Vetor alvo.
            coords (array-like): Matriz de coordenadas.

        Returns:
            float: Valor do MSE resultante do LOOCV.
        """
        X_full      = add_intercept(np.asarray(X, dtype=float))
        y_full      = np.asarray(y, dtype=float).reshape(-1)
        coords_full = np.asarray(coords, dtype=float)

        # salva estado
        old = (
            getattr(self, "X_", None),
            getattr(self, "y_", None),
            getattr(self, "coords_", None),
            getattr(self, "is_fitted_", False),
        )

        self.X_      = X_full
        self.y_      = y_full
        self.coords_ = coords_full
        self.is_fitted_ = True

        errs = np.array([
            (y_full[i] - float(X_full[i] @ self._local_beta(coords_full[i], loo_idx=i))) ** 2
            for i in range(len(X_full))
        ])

        # restaura estado
        self.X_, self.y_, self.coords_, self.is_fitted_ = old

        return float(np.mean(errs))


def estimate_bw_bounds(coords, sample_size=500, random_state=42):
    """
    Estima limites heurísticos mínimo e máximo para a largura de banda (bandwidth) 
    analisando os quantis das distâncias entre uma amostra dos dados.

    Args:
        coords (array-like): Matriz com todas as coordenadas disponíveis.
        sample_size (int, opcional): Tamanho da amostra a ser utilizado (padrão=500).
        random_state (int, opcional): Semente de aleatoriedade (padrão=42).

    Returns:
        tuple: (limite_inferior, limite_superior) de bandwidths plausíveis em km.
    """
    coords = np.asarray(coords, dtype=float)
    n      = len(coords)
    rng    = np.random.default_rng(random_state)
    idx    = rng.choice(n, size=min(n, sample_size), replace=False)
    coords_s = coords[idx]

    dists = np.concatenate([
        haversine_vector(coords_s[i], coords_s)[haversine_vector(coords_s[i], coords_s) > 0]
        for i in range(len(coords_s))
    ])

    if len(dists) == 0:
        return 10.0, 500.0

    return (
        max(5.0,  float(np.quantile(dists, 0.05))),
        max(50.0, float(np.quantile(dists, 0.50))),
    )


def golden_search_loocv(
    X, y, coords,
    kernel="gaussian",
    ridge=1e-6,
    bw_min=None,
    bw_max=None,
    tol=20.0,
    max_iter=10,
    verbose=True,
):
    """
    Realiza uma busca pela razão áurea (Golden Section Search) para encontrar a 
    largura de banda (bandwidth) que minimiza o MSE-LOOCV do GWR.

    Args:
        X (array-like): Matriz de features de treino.
        y (array-like): Vetor alvo de treino.
        coords (array-like): Coordenadas de treino.
        kernel (str, opcional): Tipo de kernel espacial (padrão: "gaussian").
        ridge (float, opcional): Constante de regularização Ridge.
        bw_min (float, opcional): Valor mínimo estrito do espaço de busca.
        bw_max (float, opcional): Valor máximo estrito do espaço de busca.
        tol (float, opcional): Tolerância da diferença para critério de parada (padrão: 20.0 km).
        max_iter (int, opcional): Número máximo de iterações de busca (padrão: 10).
        verbose (bool, opcional): Imprime os logs de progresso (padrão: True).

    Returns:
        tuple: 
            - float: Largura de banda ótima encontrada em km.
            - float: Menor LOOCV-MSE encontrado.
            - pd.DataFrame: Histórico das iterações com os bandwidths testados e seus MSEs.
    """
    X      = np.asarray(X, dtype=float)
    y      = np.asarray(y, dtype=float).reshape(-1)
    coords = np.asarray(coords, dtype=float)

    if bw_min is None or bw_max is None:
        auto_min, auto_max = estimate_bw_bounds(coords)
        bw_min = auto_min if bw_min is None else bw_min
        bw_max = auto_max if bw_max is None else bw_max

    if bw_min <= 0 or bw_max <= bw_min:
        raise ValueError(f"Faixa inválida: bw_min={bw_min:.2f}, bw_max={bw_max:.2f}")

    phi    = (1 + math.sqrt(5)) / 2
    invphi = 1 / phi

    a, b = float(bw_min), float(bw_max)
    c    = b - (b - a) * invphi
    d    = a + (b - a) * invphi

    cache = {}

    def objective(bw):
        key = round(float(bw), 4)
        if key not in cache:
            model = GeographicallyWeightedRegression(bandwidth=bw, kernel=kernel, ridge=ridge)
            cache[key] = model.loocv_mse(X, y, coords)
            if verbose:
                print(f"  [LOOCV] bw={bw:8.2f} km  ->  MSE={cache[key]:.6f}")
        return cache[key]

    fc, fd = objective(c), objective(d)

    for _ in range(max_iter):
        if (b - a) <= tol:
            break
        if fc < fd:
            b, d, fd = d, c, fc
            c  = b - (b - a) * invphi
            fc = objective(c)
        else:
            a, c, fc = c, d, fd
            d  = a + (b - a) * invphi
            fd = objective(d)

    bw_opt   = (a + b) / 2.0
    best_mse = objective(bw_opt)

    history = (
        pd.DataFrame([{"bandwidth_km": k, "loocv_mse": v} for k, v in cache.items()])
        .sort_values("bandwidth_km")
        .reset_index(drop=True)
    )

    return bw_opt, best_mse, history


def fit_predict_gwr(
    train_df,
    test_df,
    selected_features,
    coord_cols=("longitude", "latitude"),
    kernel="gaussian",
    ridge=1e-6,
    bw_min=None,
    bw_max=None,
    bw_tol=5.0,
    bw_max_iter=15,
    verbose=True,
):
    """
    Pipeline completo: prepara os dados, realiza a busca pelo bandwidth ótimo, ajusta 
    o modelo GWR aos dados de treinamento e emite as predições para os dados de teste.

    Processos englobados:
    1. Extração e limpeza de dados infinitos (NaN handling).
    2. Imputação de dados faltantes via mediana.
    3. Escalonamento das features via Z-score (StandardScaler).
    4. Otimização do bandwidth via Golden Section Search com LOOCV.
    5. Treinamento final e inferência usando o valor ótimo encontrado.

    Args:
        train_df (pd.DataFrame): DataFrame contendo os dados de treinamento.
        test_df (pd.DataFrame): DataFrame contendo os dados de teste.
        selected_features (list): Lista com os nomes das colunas de features a usar.
        coord_cols (tuple, opcional): Nomes das colunas de coordenada espacial. 
                                      Padrão é ("longitude", "latitude").
        kernel (str, opcional): Tipo de kernel espacial (padrão: "gaussian").
        ridge (float, opcional): Parâmetro de penalidade Ridge (padrão: 1e-6).
        bw_min (float, opcional): Limite inferior para busca do bandwidth ótimo.
        bw_max (float, opcional): Limite superior para busca do bandwidth ótimo.
        bw_tol (float, opcional): Tolerância de parada da otimização (padrão: 5.0).
        bw_max_iter (int, opcional): Máx. de iterações da otimização (padrão: 15).
        verbose (bool, opcional): Se True, imprime logs.

    Returns:
        dict: Um dicionário com as predições cortadas em zero, o modelo ajustado, 
              objetos do pipeline (imputer e scaler) e metadados da otimização.
              Chaves: "yhat", "bandwidth_km", "loocv_mse", "bw_history", 
                      "selected_features", "gwr_model", "imputer", "scaler".
    """
    lon_col, lat_col = coord_cols

    X_train = train_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()
    X_test  = test_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()

    y_train = train_df["y_next"].astype(float).values
    y_test  = test_df["y_next"].astype(float).values

    coords_train = train_df[[lon_col, lat_col]].astype(float).values
    coords_test  = test_df[[lon_col, lat_col]].astype(float).values

    imputer = SimpleImputer(strategy="median")
    scaler  = StandardScaler()

    X_train_sc = scaler.fit_transform(imputer.fit_transform(X_train))
    X_test_sc  = scaler.transform(imputer.transform(X_test))

    print("\n" + "=" * 140)
    print("GWR — GOLDEN SEARCH + LOOCV")
    print("=" * 140)

    bw_opt, loocv_mse, bw_history = golden_search_loocv(
        X=X_train_sc,
        y=y_train,
        coords=coords_train,
        kernel=kernel,
        ridge=ridge,
        bw_min=bw_min,
        bw_max=bw_max,
        tol=bw_tol,
        max_iter=bw_max_iter,
        verbose=verbose,
    )

    print(f"\nBandwidth ótimo : {bw_opt:.4f} km")
    print(f"LOOCV-MSE treino: {loocv_mse:.6f}")

    gwr = GeographicallyWeightedRegression(bandwidth=bw_opt, kernel=kernel, ridge=ridge)
    gwr.fit(X_train_sc, y_train, coords_train)

    # Força que as previsões não sejam negativas
    yhat = np.maximum(0, gwr.predict(X_test_sc, coords_test))

    return {
        "yhat":              yhat,
        "bandwidth_km":      bw_opt,
        "loocv_mse":         loocv_mse,
        "bw_history":        bw_history,
        "selected_features": selected_features,
        "gwr_model":         gwr,
        "imputer":           imputer,
        "scaler":            scaler,
    }