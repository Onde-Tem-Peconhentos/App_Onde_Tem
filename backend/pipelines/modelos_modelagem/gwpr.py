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


def poisson_deviance(y, y_pred):
    """
    Calcula a deviance global para um modelo de Poisson.
    """
    y_pred = np.maximum(y_pred, 1e-12)
    term1 = np.zeros_like(y)
    mask = y > 0
    term1[mask] = y[mask] * np.log(y[mask] / y_pred[mask])
    return 2 * np.sum(term1 - (y - y_pred))


def weighted_poisson_beta(X, y, w, offset=None, max_iter=100, tol=1e-5):
    """
    Calcula os coeficientes (betas) locais para uma Regressão de Poisson Ponderada.
    Utiliza o algoritmo Iteratively Reweighted Least Squares (IRLS).

    Args:
        X (array-like): Matriz de features de formato (n, p).
        y (array-like): Vetor de variáveis alvo (contagens) de formato (n,).
        w (array-like): Vetor de pesos espaciais de formato (n,).
        offset (array-like, opcional): Vetor log-transformado da variável de exposição.
        max_iter (int, opcional): Número máximo de iterações do IRLS.
        tol (float, opcional): Tolerância para o critério de convergência.

    Returns:
        np.ndarray: Vetor 1D com os coeficientes iterativos da regressão.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    
    n, p = X.shape
    if offset is None:
        offset = np.zeros(n)
    else:
        offset = np.asarray(offset, dtype=float).reshape(-1)
        
    beta = np.zeros(p)
    
    for _ in range(max_iter):
        eta = X @ beta
        # Adiciona o offset no preditor linear e clipa para evitar overflow no np.exp
        eta_offset = np.clip(eta + offset, -250, 250)
        mu = np.exp(eta_offset)
        
        # Previne divisão por zero (A_i matrix)
        mu_safe = np.maximum(mu, 1e-10)
        
        # Variável dependente ajustada (z)
        z = eta + (y - mu) / mu_safe
        
        # Pesos para o WLS interno da iteração (W * A) onde A = diag(mu)
        W_irls = w * mu
        sw = np.sqrt(np.maximum(W_irls, 1e-12)).reshape(-1, 1)
        
        Xw = X * sw
        zw = (z * sw.reshape(-1)).reshape(-1, 1)
        
        try:
            beta_new = np.linalg.pinv(Xw.T @ Xw) @ (Xw.T @ zw)
            beta_new = beta_new.reshape(-1)
        except np.linalg.LinAlgError:
            break
            
        if np.max(np.abs(beta_new - beta)) < tol:
            beta = beta_new
            break
            
        beta = beta_new
        
    return beta


class GeographicallyWeightedPoissonRegression:
    """
    Implementação de uma Regressão de Poisson Geograficamente Ponderada (GWPR).
    Suporta bandwidth fixo (em km) e adaptativo (k vizinhos), além de aceitar offsets.

    Em modo adaptativo (`adaptive=True`), o parâmetro `bandwidth` é interpretado como
    o número inteiro k de vizinhos.

    Atributos:
        bandwidth (float): Largura de banda em km (fixo) ou número de vizinhos k (adaptativo).
        kernel (str): Tipo de kernel espacial ("gaussian" ou "bisquare").
        adaptive (bool): Se True, usa bandwidth adaptativo por k vizinhos mais próximos.
        is_fitted_ (bool): Indica se o modelo já foi ajustado aos dados.
        betas_ (dict): Dicionário mapeando (lon, lat) para o vetor de betas local.
    """

    def __init__(self, bandwidth, kernel="gaussian", adaptive=False):
        self.bandwidth  = float(bandwidth)
        self.kernel     = kernel
        self.adaptive   = adaptive
        self.is_fitted_ = False
        self.betas_     = {}

    def fit(self, X, y, coords, offset=None):
        """
        Ajusta o modelo GWPR pré-calculando e armazenando os betas para cada localidade de treino.
        """
        self.X_      = add_intercept(np.asarray(X, dtype=float))
        self.y_      = np.asarray(y, dtype=float).reshape(-1)
        self.coords_ = np.asarray(coords, dtype=float)
        
        if offset is None:
            self.offset_ = np.zeros(len(self.y_))
        else:
            self.offset_ = np.asarray(offset, dtype=float).reshape(-1)
        
        self.betas_ = {}
        for i, coord in enumerate(self.coords_):
            key = (round(coord[0], 6), round(coord[1], 6))
            if key not in self.betas_:
                self.betas_[key] = self._local_beta(coord)

        self.is_fitted_ = True
        return self

    def _adaptive_bandwidth(self, dist_km, loo_idx=None):
        k = max(1, int(round(self.bandwidth)))
        d = dist_km.copy()
        if loo_idx is not None:
            d[loo_idx] = np.inf
        sorted_d = np.sort(d[d > 1e-10])
        k = min(k, len(sorted_d))
        return float(sorted_d[k - 1])

    def _local_beta(self, coord, loo_idx=None):
        d = haversine_vector(coord, self.coords_)

        if self.adaptive:
            bw = self._adaptive_bandwidth(d, loo_idx=loo_idx)
        else:
            bw = self.bandwidth

        w = gwr_kernel_weights(d, bw, kernel=self.kernel)

        if loo_idx is not None:
            w[loo_idx] = 0.0

        mask = w > 1e-12
        if mask.sum() < self.X_.shape[1]:
            w    = np.maximum(w, 1e-8)
            mask = np.ones(len(w), dtype=bool)

        return weighted_poisson_beta(
            self.X_[mask], 
            self.y_[mask], 
            w[mask], 
            offset=self.offset_[mask]
        )

    def predict(self, X_new, coords_new, offset_new=None):
        """
        Gera predições (contagens esperadas) para novos dados (via exp(X*beta + offset)).
        """
        if not self.is_fitted_:
            raise ValueError("Modelo não ajustado. Chame .fit() primeiro.")

        X_new      = add_intercept(np.asarray(X_new, dtype=float))
        coords_new = np.asarray(coords_new, dtype=float)
        
        if offset_new is None:
            offset_new = np.zeros(len(X_new))
        else:
            offset_new = np.asarray(offset_new, dtype=float).reshape(-1)

        preds = []
        for i in range(len(X_new)):
            coord = coords_new[i]
            key   = (round(coord[0], 6), round(coord[1], 6))

            if key in self.betas_:
                beta = self.betas_[key]
            else:
                beta = self._local_beta(coord)
                
            eta = X_new[i] @ beta + offset_new[i]
            eta = np.clip(eta, -250, 250)
            preds.append(float(np.exp(eta)))

        return np.array(preds)

    def loocv_deviance(self, X, y, coords, offset=None):
        """
        Calcula a Deviance de Poisson média via Leave-One-Out Cross-Validation.
        """
        X_full      = add_intercept(np.asarray(X, dtype=float))
        y_full      = np.asarray(y, dtype=float).reshape(-1)
        coords_full = np.asarray(coords, dtype=float)
        
        if offset is None:
            offset_full = np.zeros(len(y_full))
        else:
            offset_full = np.asarray(offset, dtype=float).reshape(-1)

        # salva estado
        old = (
            getattr(self, "X_", None),
            getattr(self, "y_", None),
            getattr(self, "coords_", None),
            getattr(self, "offset_", None),
            getattr(self, "is_fitted_", False),
            getattr(self, "betas_", {})
        )

        self.X_         = X_full
        self.y_         = y_full
        self.coords_    = coords_full
        self.offset_    = offset_full
        self.is_fitted_ = True

        y_preds_loocv = []
        for i in range(len(X_full)):
            beta_loocv = self._local_beta(coords_full[i], loo_idx=i)
            eta = X_full[i] @ beta_loocv + offset_full[i]
            eta = np.clip(eta, -250, 250)
            y_preds_loocv.append(np.exp(eta))
            
        y_preds_loocv = np.array(y_preds_loocv)
        
        # restaura estado
        self.X_, self.y_, self.coords_, self.offset_, self.is_fitted_, self.betas_ = old

        dev = poisson_deviance(y_full, y_preds_loocv)
        return float(dev / len(y_full))


def estimate_bw_bounds(coords, sample_size=500, random_state=42, adaptive=False):
    """(Inalterado - mantém a mesma lógica original)"""
    coords = np.asarray(coords, dtype=float)
    n      = len(coords)
    rng    = np.random.default_rng(random_state)
    idx    = rng.choice(n, size=min(n, sample_size), replace=False)
    coords_s = coords[idx]
    ns       = len(coords_s)

    if adaptive:
        k_min = max(5,  int(math.ceil(ns * 0.05)))
        k_max = max(10, int(math.ceil(ns * 0.50)))
        return float(k_min), float(k_max)

    dists = np.concatenate([
        haversine_vector(coords_s[i], coords_s)[haversine_vector(coords_s[i], coords_s) > 0]
        for i in range(ns)
    ])

    if len(dists) == 0:
        return 10.0, 500.0

    return (
        max(5.0,  float(np.quantile(dists, 0.05))),
        max(50.0, float(np.quantile(dists, 0.50))),
    )


def golden_search_loocv_poisson(
    X, y, coords,
    offset=None,
    kernel="gaussian",
    adaptive=False,
    bw_min=None,
    bw_max=None,
    tol=20.0,
    max_iter=10,
    verbose=True,
):
    """
    Busca heurística otimizando para a Deviance LOOCV do modelo de Poisson.
    """
    X      = np.asarray(X, dtype=float)
    y      = np.asarray(y, dtype=float).reshape(-1)
    coords = np.asarray(coords, dtype=float)

    if bw_min is None or bw_max is None:
        auto_min, auto_max = estimate_bw_bounds(coords, adaptive=adaptive)
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
    bw_label = "k" if adaptive else "km"

    def objective(bw):
        bw_eval = int(round(bw)) if adaptive else round(float(bw), 4)
        if bw_eval not in cache:
            model = GeographicallyWeightedPoissonRegression(
                bandwidth=bw_eval, kernel=kernel, adaptive=adaptive
            )
            # Otimizamos minimizando a Deviance LOOCV
            cache[bw_eval] = model.loocv_deviance(X, y, coords, offset=offset)
            if verbose:
                print(f"  [LOOCV] bw={bw_eval:>8}  {bw_label}  ->  Deviance/n={cache[bw_eval]:.6f}")
        return cache[bw_eval]

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

    bw_opt_raw = (a + b) / 2.0
    bw_opt     = int(round(bw_opt_raw)) if adaptive else bw_opt_raw
    best_dev   = objective(bw_opt)

    col_name = "bandwidth_k" if adaptive else "bandwidth_km"
    history = (
        pd.DataFrame([{col_name: k, "loocv_deviance": v} for k, v in cache.items()])
        .sort_values(col_name)
        .reset_index(drop=True)
    )

    return float(bw_opt), best_dev, history


def fit_predict_gwpr(
    train_df,
    test_df,
    selected_features,
    coord_cols=("longitude", "latitude"),
    offset_col=None,
    kernel="gaussian",
    adaptive=False,
    bw_min=None,
    bw_max=None,
    bw_tol=5.0,
    bw_max_iter=15,
    verbose=True,
):
    """
    Pipeline completo GWPR. Incorpora tratamento para o parâmetro `offset_col` opcional.
    """
    lon_col, lat_col = coord_cols

    X_train = train_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()
    X_test  = test_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()

    y_train = train_df["y_next"].astype(float).values
    y_test  = test_df["y_next"].astype(float).values
    
    # Tratamento da variável de exposição (Offset) via log natural
    if offset_col and offset_col in train_df.columns:
        offset_train = np.log(np.maximum(train_df[offset_col].astype(float).values, 1e-10))
        offset_test  = np.log(np.maximum(test_df[offset_col].astype(float).values, 1e-10))
    else:
        offset_train = None
        offset_test  = None

    coords_train = train_df[[lon_col, lat_col]].astype(float).values
    coords_test  = test_df[[lon_col, lat_col]].astype(float).values

    imputer = SimpleImputer(strategy="median")

    X_train_sc = imputer.fit_transform(X_train)
    X_test_sc  = imputer.transform(X_test)

    if "id_municipio" in train_df.columns:
        subset_df = train_df.groupby("id_municipio").tail(1)
        idx_subset = train_df.index.get_indexer(subset_df.index)
    else:
        rng = np.random.default_rng(42)
        idx_subset = rng.choice(len(train_df), size=min(len(train_df), 645), replace=False)

    X_train_sub  = X_train_sc[idx_subset]
    y_train_sub  = y_train[idx_subset]
    coords_sub   = coords_train[idx_subset]
    offset_sub   = offset_train[idx_subset] if offset_train is not None else None

    mode_label = "ADAPTATIVO (k vizinhos)" if adaptive else "FIXO (km)"
    print("\n" + "=" * 140)
    print(f"GWPR [POISSON] [{mode_label}] — GOLDEN SEARCH + LOOCV (Amostra de {len(idx_subset)} pontos)")
    print("=" * 140)

    bw_opt, loocv_dev, bw_history = golden_search_loocv_poisson(
        X=X_train_sub,
        y=y_train_sub,
        coords=coords_sub,
        offset=offset_sub,
        kernel=kernel,
        adaptive=adaptive,
        bw_min=bw_min,
        bw_max=bw_max,
        tol=bw_tol,
        max_iter=bw_max_iter,
        verbose=verbose,
    )

    bw_unit = "vizinhos" if adaptive else "km"
    print(f"\nBandwidth ótimo : {bw_opt:.0f} {bw_unit}" if adaptive
          else f"\nBandwidth ótimo : {bw_opt:.4f} km")
    print(f"LOOCV-Deviance/n treino: {loocv_dev:.6f}")

    gwpr = GeographicallyWeightedPoissonRegression(bandwidth=bw_opt, kernel=kernel, adaptive=adaptive)
    gwpr.fit(X_train_sc, y_train, coords_train, offset=offset_train)

    yhat = np.maximum(0, gwpr.predict(X_test_sc, coords_test, offset_new=offset_test))

    bw_key = "bandwidth_k" if adaptive else "bandwidth_km"
    return {
        "yhat":              yhat,
        bw_key:              bw_opt,
        "loocv_deviance":    loocv_dev,
        "bw_history":        bw_history,
        "selected_features": selected_features,
        "gwr_model":         gwpr,
        "imputer":           imputer,
        "scaler":            None,
    }