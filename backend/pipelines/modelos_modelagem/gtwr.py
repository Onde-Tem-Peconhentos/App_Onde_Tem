import math
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.neighbors import BallTree
from joblib import Parallel, delayed

EARTH_KM = 6371.0088

# ── 1. Funções Auxiliares ────────────────────────────────────────────────────────

def anomes_to_month_index(anomes_series):
    s = anomes_series.astype(int)
    month_number = (s // 100) * 12 + ((s % 100) - 1)
    return month_number.max() - month_number

def gtwr_kernel_weights(dist, bandwidth, kernel="gaussian"):
    bw = np.where(np.asarray(bandwidth, float) <= 0, 1e-8, bandwidth)
    if kernel == "gaussian":
        return np.exp(-(dist / bw) ** 2)
    elif kernel == "exponential":
        return np.exp(-dist / bw)
    raise ValueError(f"Kernel {kernel} não suportado.")

def add_intercept(X):
    return np.column_stack([np.ones(len(X)), X])


# ── 2. Motores de Busca (Golden e Grid) ──────────────────────────────────────────

def _golden_search(objective, a, b, tol=0.25, max_iter=15):
    invphi = (math.sqrt(5) - 1) / 2
    c = b - (b - a) * invphi
    d = a + (b - a) * invphi
    fc, fd = objective(c), objective(d)
    for _ in range(max_iter):
        if (b - a) <= tol: break
        if fc < fd:
            b, d, fd = d, c, fc; c = b - (b - a) * invphi; fc = objective(c)
        else:
            a, c, fc = c, d, fd; d = a + (b - a) * invphi; fd = objective(d)
    x_opt = (a + b) / 2.0
    return x_opt, objective(x_opt)

def _grid_search(objective, a, b, n_points=15):
    grid = np.linspace(a, b, n_points)
    results = [(v, objective(v)) for v in grid]
    return min(results, key=lambda x: x[1])

def _golden_search_int(objective, a, b, max_iter=20):
    invphi = (math.sqrt(5) - 1) / 2
    cache = {}
    def f(k):
        k = int(round(k))
        if k not in cache: cache[k] = objective(k)
        return cache[k]
    c, d = int(round(b - (b - a) * invphi)), int(round(a + (b - a) * invphi))
    fc, fd = f(c), f(d)
    for _ in range(max_iter):
        if (b - a) <= 2: break
        if fc < fd:
            b, d, fd = d, c, fc; c = int(round(b - (b - a) * invphi)); fc = f(c)
        else:
            a, c, fc = c, d, fd; d = int(round(a + (b - a) * invphi)); fd = f(d)
    k_best = min(range(a, b + 1), key=f)
    return k_best, cache[k_best], cache

def _grid_search_int(objective, a, b, step=2):
    cache = {k: objective(k) for k in range(int(a), int(b) + 1, step)}
    k_best = min(cache, key=cache.get)
    return k_best, cache[k_best], cache


# ── 3. Classe Principal GTWR ─────────────────────────────────────────────────────

class GeographicallyTemporallyWeightedRegressionLegacy:
    """
    [DEPRECADO — mantido apenas como referência histórica, não é mais
    instanciado por fit_predict_gtwr(). Ver GeographicallyTemporallyWeightedRegression
    (abaixo) para a versão corrigida usada em produção.]

    BUG CONHECIDO (não corrigido nesta classe, de propósito, para preservar o
    histórico): em `_city_betas`, o termo de decaimento temporal divide `dt`
    (uma diferença de TEMPO, em unidades de mês) pelo bandwidth espacial
    `self.city_bw[c]` (uma distância em KM):
        W = ws_ref * exp(-tau * (dt / city_bw[c]) ** 2)
    Misturar unidades de tempo (meses, tipicamente 0-50) com uma distância em
    km (tipicamente 50-500) faz essa razão ser sempre minúscula, então `tau`
    (cujo range de busca era 0.001-100) praticamente não consegue afetar o
    resultado em nenhum ponto prático da busca — confirmado empiricamente:
    variar tau por 3 ordens de grandeza mudava o LOOCV-MSE apenas na 6ª casa
    decimal (às vezes nem isso). Isso tornava a etapa de busca de tau
    essencialmente um ruído, e — quando k_s também passou a ser buscado
    livremente (em vez de herdado do GWR-Adaptativo) — deixava a busca de
    k_s "às cegas" quanto à estrutura temporal, overfitando para o extremo
    do range (bw_max) buscado.
    """
    def __init__(self, bw_s, tau, kernel="gaussian", max_time_lag=None, ridge=1e-6):
        self.bw_s = int(round(float(bw_s)))
        self.tau = float(tau)
        self.kernel = kernel
        self.max_time_lag = max_time_lag
        self.ridge = float(ridge)
        self.is_fitted_ = False

    def _build_structures(self, X, y, coords, times):
        self.X_, self.y_ = add_intercept(np.asarray(X, float)), np.asarray(y, float).reshape(-1)
        self.coords_, self.times_ = np.asarray(coords, float), np.asarray(times, float).reshape(-1)
        self.p_ = self.X_.shape[1]
        
        # Agrupa por cidade única para evitar cálculos repetidos
        self.city_coords, ids = np.unique(self.coords_, axis=0, return_inverse=True)
        self.city_of_row = ids
        self.C = len(self.city_coords)
        self.rows_by_city = [np.where(ids == c)[0] for c in range(self.C)]
        self._tree = BallTree(np.radians(self.city_coords[:, ::-1]), metric="haversine")
        return self

    def _setup_neighbors(self, k_s):
        k = int(min(max(k_s, 2), self.C))
        dist, idx = self._tree.query(np.radians(self.city_coords[:, ::-1]), k=k)
        dist_km = dist * EARTH_KM
        self.nbr_idx = idx
        self.city_bw = np.where(dist_km[:, -1] <= 0, 1e-8, dist_km[:, -1]) # h_ST(i)
        self.nbr_ws = gtwr_kernel_weights(dist_km, self.city_bw[:, None], "gaussian")
        return self

    def _city_betas(self, c, q_rows, q_times, tau, loo=False):
        neigh = self.nbr_idx[c]
        ws_ref = np.concatenate([np.full(len(self.rows_by_city[nc]), self.nbr_ws[c][j]) 
                                 for j, nc in enumerate(neigh)])
        ref_rows = np.concatenate([self.rows_by_city[nc] for nc in neigh])
        
        Xr, yr, tr = self.X_[ref_rows], self.y_[ref_rows], self.times_[ref_rows]
        dt = np.abs(q_times[:, None] - tr[None, :])
        
        # W_ST = W_S * W_T
        W = ws_ref[None, :] * np.exp(-tau * (dt / self.city_bw[c]) ** 2)
        if self.max_time_lag: W = np.where(dt > self.max_time_lag, 0.0, W)
        if loo: W[ref_rows[None, :] == q_rows[:, None]] = 0.0

        # Solução de Mínimos Quadrados
        XtWX = np.einsum('bj,jp,jq->bpq', W, Xr, Xr, optimize=True)
        XtWy = np.einsum('bj,jp,j->bp', W, Xr, yr, optimize=True)
        XtWX[:, np.arange(self.p_), np.arange(self.p_)] += self.ridge
        return np.linalg.solve(XtWX, XtWy[..., None])[..., 0]

    def _loocv_mse_internal(self, tau, n_jobs=-1):
        def _work(c):
            rows = self.rows_by_city[c]
            betas = self._city_betas(c, rows, self.times_[rows], tau, loo=True)
            return rows, np.einsum('bp,bp->b', self.X_[rows], betas)
        
        res = Parallel(n_jobs=n_jobs, backend="threading")(delayed(_work)(c) for c in range(self.C))
        preds = np.empty(len(self.y_), float)
        for rows, pr in res: preds[rows] = pr
        return float(np.mean((self.y_ - preds) ** 2))

    def fit(self, X, y, coords, times, n_jobs=-1):
        self._build_structures(X, y, coords, times)._setup_neighbors(self.bw_s)
        def _work(c):
            rows = self.rows_by_city[c]
            return rows, self._city_betas(c, rows, self.times_[rows], self.tau, loo=False)
        
        res = Parallel(n_jobs=n_jobs, backend="threading")(delayed(_work)(c) for c in range(self.C))
        self.coef_ = np.empty((len(self.y_), self.p_), float)
        for rows, b in res: self.coef_[rows] = b
        self.is_fitted_ = True
        return self

    def predict(self, X_new, coords_new, times_new):
        if not self.is_fitted_: raise ValueError("Modelo não ajustado.")
        Xn = add_intercept(np.asarray(X_new, float))
        cn, tn = np.asarray(coords_new, float), np.asarray(times_new, float).reshape(-1)
        
        _, city_new = self._tree.query(np.radians(cn[:, ::-1]), k=1)
        city_new = city_new.flatten()

        preds = np.empty(len(cn), float)
        for c in np.unique(city_new):
            q = np.where(city_new == c)[0]
            betas = self._city_betas(c, np.full(len(q), -1), tn[q], self.tau, loo=False)
            preds[q] = np.einsum('bp,bp->b', Xn[q], betas)
        return preds


class GeographicallyTemporallyWeightedRegression:
    """
    GTWR — versão corrigida (substitui GeographicallyTemporallyWeightedRegressionLegacy).

    Correção: o kernel temporal não divide mais `dt` (diferença em meses)
    pelo bandwidth ESPACIAL em km — eram unidades incompatíveis, o que
    deixava `tau` praticamente sem efeito (ver docstring da versão legada
    para os números). Agora `tau` atua diretamente sobre `dt` em unidades de
    mês² (`exp(-tau * dt**2)`), que é a escala para a qual o range de busca
    de tau (log_tau_bounds, tipicamente 0.001-100) já fazia sentido — não foi
    necessário recalibrar os limites da busca, só remover a divisão indevida.
    O kernel espacial (`ws_ref`, via `city_bw`) continua correto e inalterado.
    """

    def __init__(self, bw_s, tau, kernel="gaussian", max_time_lag=None, ridge=1e-6):
        self.bw_s = int(round(float(bw_s)))
        self.tau = float(tau)
        self.kernel = kernel
        self.max_time_lag = max_time_lag
        self.ridge = float(ridge)
        self.is_fitted_ = False

    def _build_structures(self, X, y, coords, times):
        self.X_, self.y_ = add_intercept(np.asarray(X, float)), np.asarray(y, float).reshape(-1)
        self.coords_, self.times_ = np.asarray(coords, float), np.asarray(times, float).reshape(-1)
        self.p_ = self.X_.shape[1]

        self.city_coords, ids = np.unique(self.coords_, axis=0, return_inverse=True)
        self.city_of_row = ids
        self.C = len(self.city_coords)
        self.rows_by_city = [np.where(ids == c)[0] for c in range(self.C)]
        self._tree = BallTree(np.radians(self.city_coords[:, ::-1]), metric="haversine")
        return self

    def _setup_neighbors(self, k_s):
        k = int(min(max(k_s, 2), self.C))
        dist, idx = self._tree.query(np.radians(self.city_coords[:, ::-1]), k=k)
        dist_km = dist * EARTH_KM
        self.nbr_idx = idx
        self.city_bw = np.where(dist_km[:, -1] <= 0, 1e-8, dist_km[:, -1])  # h_S(i), só para o kernel espacial
        self.nbr_ws = gtwr_kernel_weights(dist_km, self.city_bw[:, None], "gaussian")
        return self

    def _city_betas(self, c, q_rows, q_times, tau, loo=False):
        neigh = self.nbr_idx[c]
        ws_ref = np.concatenate([np.full(len(self.rows_by_city[nc]), self.nbr_ws[c][j])
                                 for j, nc in enumerate(neigh)])
        ref_rows = np.concatenate([self.rows_by_city[nc] for nc in neigh])

        Xr, yr, tr = self.X_[ref_rows], self.y_[ref_rows], self.times_[ref_rows]
        dt = np.abs(q_times[:, None] - tr[None, :])

        # W_ST = W_S * W_T — W_S via city_bw (km); W_T diretamente sobre dt
        # (meses), sem misturar com a escala espacial (ver docstring da classe).
        W = ws_ref[None, :] * np.exp(-tau * dt ** 2)
        if self.max_time_lag: W = np.where(dt > self.max_time_lag, 0.0, W)
        if loo: W[ref_rows[None, :] == q_rows[:, None]] = 0.0

        XtWX = np.einsum('bj,jp,jq->bpq', W, Xr, Xr, optimize=True)
        XtWy = np.einsum('bj,jp,j->bp', W, Xr, yr, optimize=True)
        XtWX[:, np.arange(self.p_), np.arange(self.p_)] += self.ridge
        return np.linalg.solve(XtWX, XtWy[..., None])[..., 0]

    def _loocv_mse_internal(self, tau, n_jobs=-1):
        def _work(c):
            rows = self.rows_by_city[c]
            betas = self._city_betas(c, rows, self.times_[rows], tau, loo=True)
            return rows, np.einsum('bp,bp->b', self.X_[rows], betas)

        res = Parallel(n_jobs=n_jobs, backend="threading")(delayed(_work)(c) for c in range(self.C))
        preds = np.empty(len(self.y_), float)
        for rows, pr in res: preds[rows] = pr
        return float(np.mean((self.y_ - preds) ** 2))

    def fit(self, X, y, coords, times, n_jobs=-1):
        self._build_structures(X, y, coords, times)._setup_neighbors(self.bw_s)
        def _work(c):
            rows = self.rows_by_city[c]
            return rows, self._city_betas(c, rows, self.times_[rows], self.tau, loo=False)

        res = Parallel(n_jobs=n_jobs, backend="threading")(delayed(_work)(c) for c in range(self.C))
        self.coef_ = np.empty((len(self.y_), self.p_), float)
        for rows, b in res: self.coef_[rows] = b
        self.is_fitted_ = True
        return self

    def predict(self, X_new, coords_new, times_new):
        if not self.is_fitted_: raise ValueError("Modelo não ajustado.")
        Xn = add_intercept(np.asarray(X_new, float))
        cn, tn = np.asarray(coords_new, float), np.asarray(times_new, float).reshape(-1)

        _, city_new = self._tree.query(np.radians(cn[:, ::-1]), k=1)
        city_new = city_new.flatten()

        preds = np.empty(len(cn), float)
        for c in np.unique(city_new):
            q = np.where(city_new == c)[0]
            betas = self._city_betas(c, np.full(len(q), -1), tn[q], self.tau, loo=False)
            preds[q] = np.einsum('bp,bp->b', Xn[q], betas)
        return preds


# ── 4. Pipeline Principal (Fit & Predict) ────────────────────────────────────────

def fit_predict_gtwr(train_df, test_df, selected_features,
                     coord_cols=("longitude", "latitude"), time_col="anomes",
                     search_method="golden", fixed_bw_s=None, tau_fixo=None,
                     log_tau_bounds=(-3.0, 2.0), grid_points=15,
                     bw_min=8, bw_max=65, bw_step=3,
                     search_max_periods=12, min_periods_tau_search=4,
                     period_months=1,
                     n_jobs=-1, verbose=True):
    """
    Pipeline unificado do GTWR.
    Se verbose=False, a função executará sem imprimir nada no terminal.

    `search_max_periods`: quando None ou `fixed_bw_s`/`tau_fixo` já fixam
    tudo, a busca (se houver) roda sobre o painel de treino completo. Caso
    contrário, as etapas de busca de tau/k_s usam apenas os
    `search_max_periods` períodos mais recentes de treino — mas TODOS os
    municípios são mantidos. Isso é importante: reduzir municípios mudaria o
    que "k vizinhos" fisicamente significa entre a busca e o ajuste final
    (foi exatamente esse tipo de incompatibilidade de escala que causava
    bandwidths inconsistentes em GWR — ver gwr.py). Reduzir períodos é seguro
    porque cada município já é tratado separadamente (`rows_by_city`) e o
    sinal temporal que sobra ainda é suficiente para estimar tau. O ajuste
    final sempre usa o painel de treino completo, independentemente do que
    foi usado na busca.

    `period_months`: bug encontrado ao rodar cadências de período longo
    (semestre: 6 meses entre períodos; ano: 12) — `dt` vinha sempre em MESES
    brutos (`anomes_to_month_index`), e `log_tau_bounds=(-3,2)` foi calibrado
    pensando em `dt` pequeno (cadência mês/trimestre). Com `dt` grande
    (ex.: semestre, dt até 30 meses), `dt**2` fica enorme e QUALQUER tau fora
    de uma fatia minúscula do intervalo já zera `exp(-tau*dt**2)` pra todos
    os pares exceto o período mais próximo — confirmado rodando só a etapa 1
    isoladamente: LOOCV-MSE ficou IDÊNTICO (77.664986) pra 10 valores de tau
    diferentes entre 0.08 e 86. O golden search amostra os 2 primeiros pontos
    simetricamente no espaço log a partir dos bounds inteiros, então sempre
    caía nesse platô raso em vez da fatia estreita perto do limite inferior
    onde o kernel ainda é sensível — daí o tau idêntico (82.0154) pra todo
    animal em ano/semestre. Corrigido normalizando `dt` pra unidades de
    PERÍODO em vez de mês bruto (`dt_mes / period_months`): com
    `period_months` igual ao tamanho em meses da cadência (1/3/6/12 pra
    mês/trimestre/semestre/ano), `dt` fica na mesma ordem de grandeza pequena
    pra qualquer cadência, e os mesmos `log_tau_bounds` voltam a cobrir um
    intervalo útil. O ajuste final e a predição usam a mesma normalização —
    o chamador (`ajuste_modelos_unificado.py`) precisa dividir `times_fc`
    pelo mesmo `period_months` antes de chamar `.predict()` pro forecast.

    `min_periods_tau_search`: mesmo com `dt` normalizado, cadências com
    poucos períodos de treino (ano: só 2) não têm sinal temporal suficiente
    pra estimar tau de forma confiável (só 1 valor de `dt` possível além de
    zero). Abaixo de `min_periods_tau_search` períodos distintos no painel
    de busca, a busca de tau é pulada e `tau_opt=0.0` (sem decaimento
    temporal — peso vira puramente espacial) em vez de um valor sem sentido.
    """
    lon, lat = coord_cols
    X_tr = train_df[selected_features].replace([np.inf, -np.inf], np.nan)
    X_te = test_df[selected_features].replace([np.inf, -np.inf], np.nan)
    y_tr = train_df["y_next"].astype(float).values

    c_tr, c_te = train_df[[lon, lat]].astype(float).values, test_df[[lon, lat]].astype(float).values
    t_tr = anomes_to_month_index(train_df[time_col]).astype(float).values / period_months
    t_te = anomes_to_month_index(test_df[time_col]).astype(float).values / period_months

    max_t_lag = len(np.unique(t_te))
    imputer = SimpleImputer(strategy="median")
    X_tr_sc, X_te_sc = imputer.fit_transform(X_tr), imputer.transform(X_te)

    k_s_init = int(fixed_bw_s) if fixed_bw_s else int((bw_min + bw_max) / 2)

    needs_search = fixed_bw_s is None or tau_fixo is None
    periods_tr = np.sort(np.unique(t_tr))
    if needs_search and search_max_periods and len(periods_tr) > search_max_periods:
        keep_periods = periods_tr[-search_max_periods:]
        mask = np.isin(t_tr, keep_periods)
        X_search, y_search = X_tr_sc[mask], y_tr[mask]
        c_search, t_search = c_tr[mask], t_tr[mask]
        if verbose:
            n_cities = len(np.unique(c_tr, axis=0))
            print(f"[!] Busca de tau/k_s usando os {search_max_periods} períodos de treino mais "
                  f"recentes ({mask.sum()}/{len(t_tr)} linhas, todos os {n_cities} municípios "
                  f"mantidos) — ajuste final usa o painel completo.")
    else:
        X_search, y_search, c_search, t_search = X_tr_sc, y_tr, c_tr, t_tr

    eng = GeographicallyTemporallyWeightedRegression(bw_s=k_s_init, tau=1.0, max_time_lag=max_t_lag)
    eng._build_structures(X_search, y_search, c_search, t_search)._setup_neighbors(k_s_init)

    if verbose:
        print("\n" + "=" * 80 +
              "\nGTWR Huang et al. (2010) — Gaussiano; W = W_S * W_T"
              "\nLOOCV completa\n" + "=" * 80)
        if fixed_bw_s is not None:
            print(f"[!] Bandwidth espacial FIXO informado: k_s = {k_s_init} vizinhos.")

    # ── ETAPA 1: Otimizar tau ──
    if verbose:
        print(f"\n--- ETAPA 1: Otimizando tau ({search_method.upper()}) ---")
        
    n_periods_search = len(np.unique(t_search))

    if tau_fixo is not None:
        tau_opt, mse_tau = float(tau_fixo), np.nan
    elif n_periods_search < min_periods_tau_search:
        tau_opt, mse_tau = 0.0, np.nan
        if verbose:
            print(f"[!] Só {n_periods_search} período(s) distinto(s) no painel de busca "
                  f"(< min_periods_tau_search={min_periods_tau_search}) — sinal temporal "
                  f"insuficiente pra estimar tau via LOOCV (a busca ficaria monótona e pinada "
                  f"na borda de log_tau_bounds). Usando tau=0.0 (sem decaimento temporal).")
    else:
        cache_tau = {}
        def obj_tau(log_t):
            t = 10**log_t
            if t not in cache_tau:
                cache_tau[t] = eng._loocv_mse_internal(t, n_jobs)
                if verbose:
                    print(f"  [Tau] tau={t:.4f} -> MSE={cache_tau[t]:.6f}")
            return cache_tau[t]

        a, b = log_tau_bounds
        if search_method == "golden":
            log_tau_opt, mse_tau = _golden_search(obj_tau, a, b)
        else:
            log_tau_opt, mse_tau = _grid_search(obj_tau, a, b, grid_points)
        tau_opt = 10**log_tau_opt

    # ── ETAPA 2: Otimizar k_s ──
    bw_history = None
    if fixed_bw_s is not None:
        if verbose:
            print(f"\n--- ETAPA 2: Puxada. k_s FIXO = {k_s_init} ---")
        bw_s_opt, mse_final = k_s_init, mse_tau
    else:
        if verbose:
            print(f"\n--- ETAPA 2: Otimizando k_s ({search_method.upper()}) ---")
            
        def obj_bw(k):
            eng._setup_neighbors(k)
            mse = eng._loocv_mse_internal(tau_opt, n_jobs)
            if verbose: 
                print(f"  [k_s] k={k:3d} -> MSE={mse:.6f}")
            return mse
        
        if search_method == "golden":
            bw_s_opt, mse_final, cache_bw = _golden_search_int(obj_bw, bw_min, bw_max)
        else:
            bw_s_opt, mse_final, cache_bw = _grid_search_int(obj_bw, bw_min, bw_max, bw_step)
        bw_history = pd.DataFrame([{"bw_s": k, "mse": v} for k, v in cache_bw.items()]).sort_values("bw_s")

    # ── Ajuste Final e Predição ──
    if verbose:
        print("\n--- AJUSTE FINAL E PREDIÇÃO ---")
        
    gtwr = GeographicallyTemporallyWeightedRegression(bw_s=bw_s_opt, tau=tau_opt, max_time_lag=max_t_lag)
    gtwr.fit(X_tr_sc, y_tr, c_tr, t_tr, n_jobs=n_jobs)
    
    yhat = np.maximum(0, gtwr.predict(X_te_sc, c_te, t_te))
    
    return {
        "yhat": yhat, "bw_s": bw_s_opt, "tau": tau_opt,
        "loocv_mse": mse_final, "bw_history": bw_history,
        "gtwr_model": gtwr, "imputer": imputer
    }