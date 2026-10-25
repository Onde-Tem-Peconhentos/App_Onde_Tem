import math
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import BallTree
from joblib import Parallel, delayed

EARTH_KM = 6371.0088

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


class GeographicallyWeightedRegressionLegacy:
    """
    [DEPRECADO — mantido apenas como referência histórica, não é mais usado
    por fit_predict_gwr(). Ver GeographicallyWeightedRegression (abaixo) para
    a versão corrigida e usada em produção.]

    BUG CONHECIDO (não corrigido nesta classe, de propósito, para preservar o
    histórico): em modo adaptativo (`adaptive=True`), `_adaptive_bandwidth()`
    ranqueia o k-ésimo vizinho mais próximo sobre `self.coords_`, que em dados
    em painel (uma linha por município × mês) contém múltiplas linhas
    duplicadas na mesma coordenada — uma por mês. Isso faz com que um `k`
    validado sobre uma amostra de coordenadas únicas (uma linha por município,
    como em fit_predict_gwr) passe a significar, no fit/predict final sobre o
    painel completo, algo como k / n_meses_treino municípios *distintos* —
    uma incompatibilidade de escala entre o bandwidth validado via LOOCV e o
    bandwidth efetivamente aplicado. Exemplo real observado: k=200 validado
    (≈31% dos 645 municípios) colapsou para ≈4 municípios distintos quando
    aplicado sobre um painel de 48 meses (200 / 48 ≈ 4.2).

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


class GeographicallyWeightedRegression:
    """
    GWR — versão corrigida e vetorizada (substitui GeographicallyWeightedRegressionLegacy).

    Correção principal: em modo adaptativo (`adaptive=True`), o bandwidth `k`
    agora é sempre contado em MUNICÍPIOS DISTINTOS, nunca em linhas do painel.
    Dados em painel têm uma linha por (município, mês); a versão legada
    ranqueava vizinhos sobre essas linhas duplicadas, então um `k` validado
    sobre uma amostra de coordenadas únicas passava a significar, no ajuste
    final sobre o painel completo, algo como `k / n_meses` municípios
    distintos — uma incompatibilidade de escala entre o bandwidth validado via
    LOOCV e o efetivamente aplicado. Aqui, tanto a seleção via LOOCV quanto o
    ajuste final e a predição ranqueiam sempre sobre `city_coords_` (coordenadas
    únicas), então `k` significa a mesma coisa em toda parte.

    Também adota o mesmo padrão de gtwr.py (BallTree por município + regressão
    ponderada em lote por vizinhança + paralelização via joblib) em vez do loop
    Python original, que refazia a regressão ponderada quase sobre o painel
    inteiro para cada um dos municípios — o principal motivo da lentidão do
    ajuste dos modelos espaciais.
    """

    def __init__(self, bandwidth, kernel="gaussian", adaptive=False, ridge=1e-6):
        self.bandwidth  = float(bandwidth)
        self.kernel     = kernel
        self.adaptive   = adaptive
        self.ridge      = float(ridge)
        self.is_fitted_ = False

    # ------------------------------------------------------------------
    # Estruturas auxiliares: agrupa linhas do painel por município único
    # e monta uma BallTree (haversine) sobre as coordenadas únicas.
    # ------------------------------------------------------------------
    def _build_structures(self, X, y, coords):
        self.X_      = add_intercept(np.asarray(X, dtype=float))
        self.y_      = np.asarray(y, dtype=float).reshape(-1)
        self.coords_ = np.asarray(coords, dtype=float)
        self.p_      = self.X_.shape[1]

        self.city_coords_, ids = np.unique(self.coords_, axis=0, return_inverse=True)
        self.city_of_row_ = ids
        self.C_ = len(self.city_coords_)
        self.rows_by_city_ = [np.where(ids == c)[0] for c in range(self.C_)]
        self._tree = BallTree(np.radians(self.city_coords_[:, ::-1]), metric="haversine")
        return self

    def _neighbors_adaptive(self, k_cities):
        """
        k municípios distintos mais próximos de cada município, SEM contar o
        próprio (mantém a semântica original: bandwidth = distância até o
        k-ésimo vizinho OUTRO; o próprio município ainda entra na regressão
        ponderada com peso 1, só não conta para o "k").
        """
        k = int(min(max(k_cities, 1), self.C_ - 1)) if self.C_ > 1 else 1
        dist, idx = self._tree.query(
            np.radians(self.city_coords_[:, ::-1]), k=min(k + 1, self.C_)
        )
        # A primeira coluna é o próprio ponto (distância 0) — remove do "k",
        # mas mantém como referência própria dentro de _city_beta.
        return idx[:, 1:], dist[:, 1:] * EARTH_KM

    def _neighbors_fixed(self, bandwidth_km, cutoff_sigmas=4.0):
        """
        Municípios distintos dentro de um raio de corte (múltiplo do bandwidth
        fixo). Além desse raio o peso gaussiano é numericamente desprezível,
        então restringir a vizinhança evita reprocessar o país inteiro para
        cada município sem alterar o resultado de forma perceptível.
        """
        radius_km = max(cutoff_sigmas * bandwidth_km, 1.0)
        radius_km = min(radius_km, 20_100.0)  # meio-perímetro da Terra
        idx_list, dist_list = self._tree.query_radius(
            np.radians(self.city_coords_[:, ::-1]),
            r=radius_km / EARTH_KM,
            return_distance=True,
        )
        return idx_list, [d * EARTH_KM for d in dist_list]

    def _city_beta(self, c, loo=False):
        neigh    = self.nbr_idx_[c]
        dist_nbr = self.nbr_dist_[c]
        bw       = self.city_bw_[c]

        ref_rows = np.concatenate([self.rows_by_city_[nc] for nc in neigh])
        d_rows   = np.concatenate([
            np.full(len(self.rows_by_city_[nc]), dist_nbr[j])
            for j, nc in enumerate(neigh)
        ])

        w = gwr_kernel_weights(d_rows, bw, kernel=self.kernel)
        if loo:
            own = self.rows_by_city_[c]
            w = w.copy()
            w[np.isin(ref_rows, own)] = 0.0

        Xr, yr = self.X_[ref_rows], self.y_[ref_rows]
        Xw = Xr * w[:, None]
        XtWX = Xw.T @ Xr
        XtWX[np.arange(self.p_), np.arange(self.p_)] += self.ridge
        XtWy = Xw.T @ yr
        return np.linalg.solve(XtWX, XtWy)

    def _prepare_neighbors(self):
        if self.adaptive:
            k = max(1, int(round(self.bandwidth)))
            idx, dist = self._neighbors_adaptive(k)
            # bandwidth = distância até o k-ésimo OUTRO município; o próprio
            # município entra como referência com distância 0 (peso 1).
            self.city_bw_  = np.maximum(dist[:, -1], 1e-8)
            self_col = np.arange(self.C_)[:, None]
            self.nbr_idx_  = list(np.concatenate([self_col, idx], axis=1))
            self.nbr_dist_ = list(np.concatenate([np.zeros((self.C_, 1)), dist], axis=1))
        else:
            idx_list, dist_list = self._neighbors_fixed(self.bandwidth)
            self.nbr_idx_  = idx_list
            self.nbr_dist_ = dist_list
            self.city_bw_  = np.full(self.C_, max(self.bandwidth, 1e-8))

    def fit(self, X, y, coords):
        self._build_structures(X, y, coords)
        self._prepare_neighbors()

        res = Parallel(n_jobs=-1, backend="threading")(
            delayed(self._city_beta)(c, loo=False) for c in range(self.C_)
        )
        self.betas_by_city_ = np.asarray(res)
        self.is_fitted_ = True
        return self

    def _beta_for_new_coord(self, coord):
        """Coordenada fora do treino: monta vizinhança sob demanda."""
        d_city = haversine_vector(coord, self.city_coords_)
        if self.adaptive:
            k = max(1, min(int(round(self.bandwidth)), self.C_))
            order = np.argsort(d_city)[:k]
            bw = max(float(d_city[order][-1]), 1e-8)
        else:
            radius_km = min(max(4.0 * self.bandwidth, 1.0), 20_100.0)
            order = np.flatnonzero(d_city <= radius_km)
            if len(order) == 0:
                order = np.argsort(d_city)[:1]
            bw = max(self.bandwidth, 1e-8)

        ref_rows = np.concatenate([self.rows_by_city_[c] for c in order])
        d_rows   = haversine_vector(coord, self.coords_[ref_rows])
        w        = gwr_kernel_weights(d_rows, bw, kernel=self.kernel)

        Xr, yr = self.X_[ref_rows], self.y_[ref_rows]
        Xw = Xr * w[:, None]
        XtWX = Xw.T @ Xr
        XtWX[np.arange(self.p_), np.arange(self.p_)] += self.ridge
        XtWy = Xw.T @ yr
        return np.linalg.solve(XtWX, XtWy)

    def predict(self, X_new, coords_new):
        if not self.is_fitted_:
            raise ValueError("Modelo não ajustado. Chame .fit() primeiro.")

        X_new      = add_intercept(np.asarray(X_new, dtype=float))
        coords_new = np.asarray(coords_new, dtype=float)

        city_lookup = {
            (round(c[0], 6), round(c[1], 6)): i
            for i, c in enumerate(self.city_coords_)
        }

        preds = np.empty(len(X_new), dtype=float)
        for i in range(len(X_new)):
            key = (round(coords_new[i, 0], 6), round(coords_new[i, 1], 6))
            beta = (
                self.betas_by_city_[city_lookup[key]]
                if key in city_lookup
                else self._beta_for_new_coord(coords_new[i])
            )
            preds[i] = float(X_new[i] @ beta)

        return preds

    def loocv_mse(self, X, y, coords):
        """MSE via leave-one-*município*-out (todas as linhas desse município são excluídas)."""
        self._build_structures(X, y, coords)
        self._prepare_neighbors()

        def _work(c):
            rows = self.rows_by_city_[c]
            beta = self._city_beta(c, loo=True)
            return rows, self.X_[rows] @ beta

        res = Parallel(n_jobs=-1, backend="threading")(delayed(_work)(c) for c in range(self.C_))
        preds = np.empty(len(self.y_), dtype=float)
        for rows, pr in res:
            preds[rows] = pr

        self.is_fitted_ = False
        return float(np.mean((self.y_ - preds) ** 2))


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

def grid_search_loocv(
    X, y, coords,
    kernel="gaussian",
    adaptive=False,
    bw_min=None,
    bw_max=None,
    n_grid=15,
    grid_values=None,
    verbose=True,
):
    """
    Busca em grade (Grid Search) pela largura de banda (bandwidth) que minimiza
    o MSE-LOOCV do GWR.

    Avalia um conjunto de candidatos igualmente espaçados entre [bw_min, bw_max]
    (ou uma lista explícita em `grid_values`) e retorna o melhor.

    Suporta tanto bandwidth fixo (km) quanto adaptativo (k vizinhos). Em modo
    adaptativo, os candidatos são arredondados para inteiros e deduplicados;
    valores repetidos são servidos do cache.

    Args:
        X (array-like): Matriz de features de treino.
        y (array-like): Vetor alvo de treino.
        coords (array-like): Coordenadas de treino.
        kernel (str, opcional): Tipo de kernel espacial (padrão: "gaussian").
        adaptive (bool, opcional): Se True, busca sobre k vizinhos (inteiro).
        bw_min (float, opcional): Limite inferior da grade (km ou k).
        bw_max (float, opcional): Limite superior da grade (km ou k).
        n_grid (int, opcional): Número de pontos da grade (padrão: 15).
                                Ignorado se `grid_values` for fornecido.
        grid_values (array-like, opcional): Lista explícita de candidatos a testar.
                                            Sobrepõe bw_min/bw_max/n_grid.
        verbose (bool, opcional): Imprime logs de progresso (padrão: True).

    Returns:
        tuple:
            - float: Bandwidth ótimo (km em modo fixo; k inteiro em adaptativo).
            - float: Menor LOOCV-MSE encontrado.
            - pd.DataFrame: Histórico com bandwidths testados e seus MSEs.
                            Coluna: "bandwidth_km" (fixo) ou "bandwidth_k" (adaptativo).
    """
    X      = np.asarray(X, dtype=float)
    y      = np.asarray(y, dtype=float).reshape(-1)
    coords = np.asarray(coords, dtype=float)

    # ---- Define os candidatos da grade ----
    if grid_values is not None:
        candidates = np.asarray(grid_values, dtype=float)
    else:
        if bw_min is None or bw_max is None:
            auto_min, auto_max = estimate_bw_bounds(coords, adaptive=adaptive)
            bw_min = auto_min if bw_min is None else bw_min
            bw_max = auto_max if bw_max is None else bw_max

        if bw_min <= 0 or bw_max <= bw_min:
            raise ValueError(f"Faixa inválida: bw_min={bw_min:.2f}, bw_max={bw_max:.2f}")

        candidates = np.linspace(float(bw_min), float(bw_max), int(n_grid))

    # Em modo adaptativo: inteiros e deduplicados; em fixo: arredonda p/ chave de cache
    if adaptive:
        candidates = np.unique([int(round(c)) for c in candidates])
    else:
        candidates = np.unique([round(float(c), 4) for c in candidates])

    cache    = {}
    bw_label = "k" if adaptive else "km"

    def objective(bw):
        bw_eval = int(round(bw)) if adaptive else round(float(bw), 4)
        if bw_eval not in cache:
            model = GeographicallyWeightedRegression(
                bandwidth=bw_eval, kernel=kernel, adaptive=adaptive
            )
            cache[bw_eval] = model.loocv_mse(X, y, coords)
            if verbose:
                print(f"  [LOOCV] bw={bw_eval:>8}  {bw_label}  ->  MSE={cache[bw_eval]:.6f}")
        return cache[bw_eval]

    # ---- Avalia toda a grade ----
    for bw in candidates:
        objective(bw)

    # ---- Seleciona o melhor ----
    best_bw  = min(cache, key=cache.get)
    best_mse = cache[best_bw]
    bw_opt   = int(round(best_bw)) if adaptive else float(best_bw)

    col_name = "bandwidth_k" if adaptive else "bandwidth_km"
    history = (
        pd.DataFrame([{col_name: k, "loocv_mse": v} for k, v in cache.items()])
        .sort_values(col_name)
        .reset_index(drop=True)
    )

    bw_unit = "vizinhos" if adaptive else "km"
    if verbose:
        print(f"\n[GRID] Melhor bandwidth: {bw_opt:.0f} {bw_unit}  ->  MSE={best_mse:.6f}"
              if adaptive else
              f"\n[GRID] Melhor bandwidth: {bw_opt:.4f} km  ->  MSE={best_mse:.6f}")

    return float(bw_opt), best_mse, history


def fit_predict_gwr(
    train_df,
    test_df,
    selected_features,
    coord_cols=("longitude", "latitude"),
    kernel="gaussian",
    adaptive=False,
    search="golden",
    bw_min=None,
    bw_max=None,
    bw_tol=5.0,
    bw_max_iter=15,
    n_grid=15,
    grid_values=None,
    verbose=True,
):
    """
    Pipeline completo: prepara os dados, realiza a busca pelo bandwidth ótimo, ajusta
    o modelo GWR aos dados de treinamento e emite as predições para os dados de teste.

    Processos englobados:
    1. Extração e limpeza de dados infinitos (NaN handling).
    2. Imputação de dados faltantes via mediana.
    3. Otimização do bandwidth via Golden Section Search OU Grid Search com LOOCV.
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
        search (str, opcional): Método de busca do bandwidth: "golden" (Golden Section
                                Search) ou "grid" (Grid Search). Padrão: "golden".
        bw_min (float, opcional): Limite inferior da busca (km se fixo, k se adaptativo).
        bw_max (float, opcional): Limite superior da busca (km se fixo, k se adaptativo).
        bw_tol (float, opcional): Tolerância de parada (Golden Search). Padrão: 5.0.
        bw_max_iter (int, opcional): Máx. de iterações (Golden Search). Padrão: 15.
        n_grid (int, opcional): Número de pontos da grade (Grid Search). Padrão: 15.
        grid_values (array-like, opcional): Lista explícita de candidatos (Grid Search).
                                            Sobrepõe bw_min/bw_max/n_grid.
        verbose (bool, opcional): Se True, imprime logs.

    Returns:
        dict: Um dicionário com as predições cortadas em zero, o modelo ajustado,
              objetos do pipeline e metadados da otimização.
              Chaves: "yhat", "bandwidth_km" (ou "bandwidth_k"), "loocv_mse",
                      "bw_history", "search", "selected_features", "gwr_model",
                      "imputer", "scaler".
    """
    lon_col, lat_col = coord_cols

    if search not in ("golden", "grid"):
        raise ValueError(f"search inválido: {search!r}. Use 'golden' ou 'grid'.")

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

    mode_label   = "ADAPTATIVO (k vizinhos)" if adaptive else "FIXO (km)"
    search_label = "GRID SEARCH" if search == "grid" else "GOLDEN SEARCH"
    print("\n" + "=" * 140)
    print(f"GWR [{mode_label}] — {search_label} + LOOCV (Amostra de {len(idx_subset)} pontos)")
    print("=" * 140)

    if search == "grid":
        bw_opt, loocv_mse, bw_history = grid_search_loocv(
            X=X_train_sub,
            y=y_train_sub,
            coords=coords_sub,
            kernel=kernel,
            adaptive=adaptive,
            bw_min=bw_min,
            bw_max=bw_max,
            n_grid=n_grid,
            grid_values=grid_values,
            verbose=verbose,
        )
    else:
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
        "bandwidth_km":      bw_opt if not adaptive else None,
        "bandwidth_k":       bw_opt if adaptive else None,
        "loocv_mse":         loocv_mse,
        "bw_history":        bw_history,
        "search":            search,
        "selected_features": selected_features,
        "gwr_model":         gwr,
        "imputer":           imputer,
        "scaler":            None,
        "kernel":            kernel,
        "adaptive":          adaptive
    }