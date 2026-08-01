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


def weighted_beta(X, y, w):
    """
    Calcula os coeficientes (betas) de uma Regressão Linear Ponderada localmente.

    Args:
        X (array-like): Matriz de features de formato (n, p).
        y (array-like): Vetor de variáveis dependentes (alvo) de formato (n,).
        w (array-like): Vetor de pesos de formato (n,).

    Returns:
        np.ndarray: Vetor 1D com os coeficientes da regressão (incluindo intercepto se presente).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1, 1)
    w = np.asarray(w, dtype=float).reshape(-1)

    sw  = np.sqrt(w).reshape(-1, 1)
    Xw  = X * sw
    yw  = y * sw

    beta = np.linalg.pinv(Xw.T @ Xw) @ (Xw.T @ yw)
    return beta.reshape(-1)


class GeographicallyWeightedRegression:
    """
    Implementação de uma Regressão Geograficamente Ponderada (GWR) simplificada.
    Suporta bandwidth fixo (em km) e bandwidth adaptativo (k vizinhos mais próximos).

    Em modo adaptativo (`adaptive=True`), o parâmetro `bandwidth` é interpretado como
    o número inteiro k de vizinhos. Para cada ponto focal, o raio local é definido como
    a distância ao k-ésimo vizinho mais próximo — o kernel se ajusta automaticamente
    à densidade espacial local.

    A predição out-of-sample é mantida em ambos os modos:
    - Coordenadas vistas no treino: betas pré-calculados são reutilizados via lookup.
    - Coordenadas novas (não vistas): betas são calculados on-the-fly usando as
      distâncias aos pontos de treino (suportado em modo adaptativo e fixo).

    Atributos:
        bandwidth (float): Largura de banda em km (fixo) ou número de vizinhos k (adaptativo).
        kernel (str): Tipo de kernel espacial ("gaussian" ou "bisquare").
        adaptive (bool): Se True, usa bandwidth adaptativo por k vizinhos mais próximos.
        is_fitted_ (bool): Indica se o modelo já foi ajustado (fit) aos dados.
        betas_ (dict): Dicionário mapeando (lon, lat) para o vetor de betas local.
    """

    def __init__(self, bandwidth, kernel="gaussian", adaptive=False):
        self.bandwidth  = float(bandwidth)
        self.kernel     = kernel
        self.adaptive   = adaptive
        self.is_fitted_ = False
        self.betas_     = {}

    def fit(self, X, y, coords):
        """
        Ajusta o modelo GWR armazenando as features, target e coordenadas de treino,
        além de pré-calcular e armazenar os betas para cada localidade única.
        """
        self.X_      = add_intercept(np.asarray(X, dtype=float))
        self.y_      = np.asarray(y, dtype=float).reshape(-1)
        self.coords_ = np.asarray(coords, dtype=float)
        
        self.betas_ = {}
        # Pré-calcula os betas para cada coordenada no treino
        for coord in self.coords_:
            # Arredondamos para 6 casas decimais para evitar erros de precisão de ponto flutuante na chave do dict
            key = (round(coord[0], 6), round(coord[1], 6))
            if key not in self.betas_:
                self.betas_[key] = self._local_beta(coord)

        self.is_fitted_ = True
        return self

    def _adaptive_bandwidth(self, dist_km, loo_idx=None):
        """
        Calcula o bandwidth local para o modo adaptativo: distância ao k-ésimo
        vizinho mais próximo (excluindo o próprio ponto focal em LOOCV).

        Args:
            dist_km (np.ndarray): Vetor de distâncias em km a todos os pontos de treino.
            loo_idx (int, opcional): Índice a excluir (LOOCV). Se fornecido, esse ponto
                                     recebe distância infinita antes de ordenar.

        Returns:
            float: Distância ao k-ésimo vizinho (bandwidth local).
        """
        k = max(1, int(round(self.bandwidth)))
        d = dist_km.copy()
        if loo_idx is not None:
            d[loo_idx] = np.inf
        # Exclui o ponto focal em si (distância zero) para não contar como vizinho
        sorted_d = np.sort(d[d > 1e-10])
        k = min(k, len(sorted_d))
        return float(sorted_d[k - 1])

    def _local_beta(self, coord, loo_idx=None):
        """
        Calcula os coeficientes (betas) locais para uma única coordenada.

        Em modo adaptativo, o bandwidth é o raio até o k-ésimo vizinho mais próximo.
        Em modo fixo, o bandwidth é o valor em km definido no construtor.
        """
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

        return weighted_beta(
            self.X_[mask], self.y_[mask], w[mask]
        )

    def predict(self, X_new, coords_new):
        """
        Gera predições para novos dados.

        Para coordenadas já vistas no treino, reutiliza os betas pré-calculados
        via lookup (chave lon/lat arredondada a 6 casas decimais).

        Para coordenadas genuinamente novas (out-of-sample), o beta local é
        calculado on-the-fly usando as distâncias aos pontos de treino —
        funciona tanto em modo fixo quanto adaptativo.

        Args:
            X_new (array-like): Features dos pontos a prever (sem intercepto).
            coords_new (array-like): Coordenadas [longitude, latitude] dos pontos a prever.

        Returns:
            np.ndarray: Vetor de predições.
        """
        if not self.is_fitted_:
            raise ValueError("Modelo não ajustado. Chame .fit() primeiro.")

        X_new      = add_intercept(np.asarray(X_new, dtype=float))
        coords_new = np.asarray(coords_new, dtype=float)

        preds = []
        for i in range(len(X_new)):
            coord = coords_new[i]
            key   = (round(coord[0], 6), round(coord[1], 6))

            if key in self.betas_:
                beta = self.betas_[key]
            else:
                # Coordenada nova: calcula beta on-the-fly
                beta = self._local_beta(coord)

            preds.append(float(X_new[i] @ beta))

        return np.array(preds)

    def loocv_mse(self, X, y, coords):
        """
        Calcula o Erro Quadrático Médio (MSE) via Leave-One-Out Cross-Validation.
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
            getattr(self, "betas_", {})
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
        self.X_, self.y_, self.coords_, self.is_fitted_, self.betas_ = old

        return float(np.mean(errs))


def estimate_bw_bounds(coords, sample_size=500, random_state=42, adaptive=False):
    """
    Estima limites heurísticos mínimo e máximo para a largura de banda (bandwidth).

    Em modo fixo (adaptive=False): retorna quantis de distância em km.
    Em modo adaptativo (adaptive=True): retorna limites para k (número de vizinhos),
    baseados em frações do tamanho da amostra.

    Args:
        coords (array-like): Matriz com todas as coordenadas disponíveis.
        sample_size (int, opcional): Tamanho da amostra a ser utilizado (padrão=500).
        random_state (int, opcional): Semente de aleatoriedade (padrão=42).
        adaptive (bool, opcional): Se True, retorna limites para k (vizinhos).

    Returns:
        tuple: (limite_inferior, limite_superior) em km (fixo) ou em k vizinhos (adaptativo).
    """
    coords = np.asarray(coords, dtype=float)
    n      = len(coords)
    rng    = np.random.default_rng(random_state)
    idx    = rng.choice(n, size=min(n, sample_size), replace=False)
    coords_s = coords[idx]
    ns       = len(coords_s)

    if adaptive:
        # k mínimo: ~5% dos pontos da amostra; k máximo: ~50% (pelo menos 10)
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


def golden_search_loocv(
    X, y, coords,
    kernel="gaussian",
    adaptive=False,
    bw_min=None,
    bw_max=None,
    tol=20.0,
    max_iter=10,
    verbose=True,
):
    """
    Realiza uma busca pela razão áurea (Golden Section Search) para encontrar a 
    largura de banda (bandwidth) que minimiza o MSE-LOOCV do GWR.

    Suporta tanto bandwidth fixo (em km) quanto adaptativo (k vizinhos).
    Em modo adaptativo, os candidatos são arredondados para inteiros antes de avaliar,
    e valores duplicados são servidos do cache — evitando recomputação.

    Args:
        X (array-like): Matriz de features de treino.
        y (array-like): Vetor alvo de treino.
        coords (array-like): Coordenadas de treino.
        kernel (str, opcional): Tipo de kernel espacial (padrão: "gaussian").
        adaptive (bool, opcional): Se True, busca sobre k vizinhos (inteiro). Padrão: False.
        bw_min (float, opcional): Valor mínimo do espaço de busca (km ou k).
        bw_max (float, opcional): Valor máximo do espaço de busca (km ou k).
        tol (float, opcional): Tolerância de parada. Em modo fixo: km; adaptativo: vizinhos.
                               Padrão: 20.0.
        max_iter (int, opcional): Número máximo de iterações de busca (padrão: 10).
        verbose (bool, opcional): Imprime os logs de progresso (padrão: True).

    Returns:
        tuple: 
            - float: Bandwidth ótimo (km em modo fixo; k inteiro em modo adaptativo).
            - float: Menor LOOCV-MSE encontrado.
            - pd.DataFrame: Histórico das iterações com os bandwidths testados e seus MSEs.
                            Coluna: "bandwidth_km" (fixo) ou "bandwidth_k" (adaptativo).
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
        # Em modo adaptativo, k deve ser inteiro; arredonda antes de usar como chave
        bw_eval = int(round(bw)) if adaptive else round(float(bw), 4)
        if bw_eval not in cache:
            model = GeographicallyWeightedRegression(
                bandwidth=bw_eval, kernel=kernel, adaptive=adaptive
            )
            cache[bw_eval] = model.loocv_mse(X, y, coords)
            if verbose:
                print(f"  [LOOCV] bw={bw_eval:>8}  {bw_label}  ->  MSE={cache[bw_eval]:.6f}")
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
    best_mse   = objective(bw_opt)

    col_name = "bandwidth_k" if adaptive else "bandwidth_km"
    history = (
        pd.DataFrame([{col_name: k, "loocv_mse": v} for k, v in cache.items()])
        .sort_values(col_name)
        .reset_index(drop=True)
    )

    return float(bw_opt), best_mse, history


def fit_predict_gwr(
    train_df,
    test_df,
    selected_features,
    coord_cols=("longitude", "latitude"),
    kernel="gaussian",
    adaptive=False,
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
    3. Otimização do bandwidth via Golden Section Search com LOOCV.
    4. Treinamento final e inferência usando o valor ótimo encontrado.

    Args:
        train_df (pd.DataFrame): DataFrame contendo os dados de treinamento.
        test_df (pd.DataFrame): DataFrame contendo os dados de teste.
        selected_features (list): Lista com os nomes das colunas de features a usar.
        coord_cols (tuple, opcional): Nomes das colunas de coordenada espacial. 
                                      Padrão é ("longitude", "latitude").
        kernel (str, opcional): Tipo de kernel espacial (padrão: "gaussian").
        adaptive (bool, opcional): Se True, usa bandwidth adaptativo (k vizinhos).
                                   Se False, bandwidth fixo em km (padrão: False).
        bw_min (float, opcional): Limite inferior da busca (km se fixo, k se adaptativo).
        bw_max (float, opcional): Limite superior da busca (km se fixo, k se adaptativo).
        bw_tol (float, opcional): Tolerância de parada (padrão: 5.0).
        bw_max_iter (int, opcional): Máx. de iterações da otimização (padrão: 15).
        verbose (bool, opcional): Se True, imprime logs.

    Returns:
        dict: Um dicionário com as predições cortadas em zero, o modelo ajustado, 
              objetos do pipeline e metadados da otimização.
              Chaves: "yhat", "bandwidth_km" (ou "bandwidth_k"), "loocv_mse",
                      "bw_history", "selected_features", "gwr_model", "imputer", "scaler".
    """
    lon_col, lat_col = coord_cols

    X_train = train_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()
    X_test  = test_df[selected_features].replace([np.inf, -np.inf], np.nan).copy()

    y_train = train_df["y_next"].astype(float).values
    y_test  = test_df["y_next"].astype(float).values

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

    X_train_sub = X_train_sc[idx_subset]
    y_train_sub = y_train[idx_subset]
    coords_sub  = coords_train[idx_subset]

    mode_label = "ADAPTATIVO (k vizinhos)" if adaptive else "FIXO (km)"
    print("\n" + "=" * 140)
    print(f"GWR [{mode_label}] — GOLDEN SEARCH + LOOCV (Amostra de {len(idx_subset)} pontos)")
    print("=" * 140)

    bw_opt, loocv_mse, bw_history = golden_search_loocv(
        X=X_train_sub,
        y=y_train_sub,
        coords=coords_sub,
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
    print(f"LOOCV-MSE treino: {loocv_mse:.6f}")

    gwr = GeographicallyWeightedRegression(bandwidth=bw_opt, kernel=kernel, adaptive=adaptive)
    gwr.fit(X_train_sc, y_train, coords_train)

    yhat = np.maximum(0, gwr.predict(X_test_sc, coords_test))

    bw_key = "bandwidth_k" if adaptive else "bandwidth_km"
    return {
        "yhat":              yhat,
        bw_key:              bw_opt,
        "loocv_mse":         loocv_mse,
        "bw_history":        bw_history,
        "selected_features": selected_features,
        "gwr_model":         gwr,
        "imputer":           imputer,
        "scaler":            None,
    }