// src/components/ModelComparisonTable.jsx
import React, { useEffect, useState } from "react";
import styles from "../pages/styles/Modelos.module.css";

const METODO_LABELS = {
  ols: "OLS Global",
  gwr: "GWR (Gaussiano)",
  gwr_adaptativo: "GWR-Adaptativo",
  gtwr: "GTWR (Espaço-Temporal)",
  baseline_zero: "Baseline: zero",
  baseline_persistencia: "Baseline: persistência",
  baseline_media_municipal: "Baseline: média municipal",
  baseline_xgboost: "Baseline: XGBoost",
};

// baseline_xgboost fica fora deste set de propósito: diferente dos outros
// 3 baselines (triviais, sem features), ele usa as mesmas selected_features
// dos modelos reais — então o "gain vs. média municipal" dele é uma
// comparação válida e relevante, não deve ficar escondido como "—".
const METODOS_BASELINE = new Set(["baseline_zero", "baseline_persistencia", "baseline_media_municipal"]);

function fmt(v, digits = 3) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

function fmtPercent(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(1)}%`;
}

// Referências fixas do universo de municípios do pipeline (São Paulo):
// total de municípios e distância média entre pares de municípios (haversine,
// calculada uma vez sobre as 207.690 combinações de 645 municípios — não
// muda entre execuções, então fica fixo aqui em vez de recalculado no cliente).
const TOTAL_MUNICIPIOS = 645;
const DISTANCIA_MEDIA_KM = 276.1;

function BandwidthCell({ row }) {
  if (row.gwr_bandwidth_km !== null && row.gwr_bandwidth_km !== undefined) {
    const razao = row.gwr_bandwidth_km / DISTANCIA_MEDIA_KM;
    return (
      <>
        {fmt(row.gwr_bandwidth_km, 1)} km
        <div className={styles.comparisonSub}>
          {razao.toFixed(2)}× a distância média entre municípios ({DISTANCIA_MEDIA_KM} km)
        </div>
      </>
    );
  }

  if (row.gwr_bandwidth_k !== null && row.gwr_bandwidth_k !== undefined) {
    const pct = ((row.gwr_bandwidth_k / TOTAL_MUNICIPIOS) * 100).toFixed(0);
    return (
      <>
        {row.gwr_bandwidth_k} vizinhos
        <div className={styles.comparisonSub}>
          {pct}% dos {TOTAL_MUNICIPIOS} municípios
        </div>
      </>
    );
  }

  if (row.gtwr_bandwidth_s !== null && row.gtwr_bandwidth_s !== undefined) {
    const pct = ((row.gtwr_bandwidth_s / TOTAL_MUNICIPIOS) * 100).toFixed(0);
    return (
      <>
        {row.gtwr_bandwidth_s} vizinhos
        <div className={styles.comparisonSub}>
          {pct}% dos {TOTAL_MUNICIPIOS} municípios
          {row.gtwr_tau !== null && row.gtwr_tau !== undefined && <>, τ={fmt(row.gtwr_tau, 4)}</>}
        </div>
      </>
    );
  }

  return "—";
}

/**
 * Tabela comparativa de todos os modelos vs. baselines PARA O ANIMAL E
 * PERÍODO escolhidos nos filtros da página — não para todos os animais (essa
 * era a versão anterior). O método atualmente selecionado no filtro
 * "Modelo" aparece em negrito, com um selo, para ficar claro qual dos
 * modelos abaixo (ModelDetails) está com o detalhamento aberto.
 */
export default function ModelComparisonTable({ animal, tipoPeriodo, metodoSelecionado }) {
  const [resultados, setResultados] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!animal || !tipoPeriodo) return;

    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ tipo_periodo: tipoPeriodo, animal });
    fetch(`http://localhost:8000/api/modelo/comparativo?${params.toString()}`)
      .then((r) => {
        if (!r.ok) throw new Error(`Erro HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        setResultados(json.resultados || []);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [animal, tipoPeriodo]);

  if (!animal || !tipoPeriodo) return null;

  if (loading) {
    return (
      <section className={styles.comparisonSection}>
        <p className={styles.mapCaption}>Carregando tabela comparativa...</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className={styles.comparisonSection}>
        <p className={styles.mapCaption}>Não foi possível carregar a tabela comparativa: {error}</p>
      </section>
    );
  }

  if (!resultados || resultados.length === 0) {
    return null;
  }

  const linhas = [...resultados].sort((a, b) => (a.mse ?? Infinity) - (b.mse ?? Infinity));
  const melhorMetodo = linhas[0]?.metodo;
  const metodoFiltro = metodoSelecionado?.toLowerCase();

  return (
    <section className={styles.comparisonSection}>
      <h3 className={styles.sectionTitle}>
        Comparativo: {animal} — {tipoPeriodo}
      </h3>
      <p className={styles.mapCaption}>
        {/* Todos os modelos e baselines para o animal e período selecionados
        acima. Todas as métricas abaixo são calculadas sobre o conjunto de{" "}
        <strong>teste</strong> (nunca visto no ajuste do modelo) — nunca de
        treino. Ordenado por MSE (menor é melhor); em <strong>negrito</strong>,
        o modelo escolhido no filtro "Modelo" (detalhado acima). */}
      </p>

      <div style={{ overflowX: "auto" }}>
        <table className={styles.comparisonTable}>
          <thead>
            <tr>
              <th>Modelo</th>
              <th>MSE (teste)</th>
              <th>R² (teste)</th>
              <th>Ganho vs. média mun.</th>
              <th>Bandwidth</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((row) => {
              const isSelecionado = row.metodo === metodoFiltro;
              const isMelhor = row.metodo === melhorMetodo;
              return (
                <tr
                  key={row.metodo}
                  className={isMelhor ? styles.comparisonRowBest : undefined}
                  style={isSelecionado ? { fontWeight: 700 } : undefined}
                >
                  <td>
                    {METODO_LABELS[row.metodo] || row.metodo}
                    {isMelhor && <span className={styles.comparisonBadgeBest}>melhor</span>}
                    {isSelecionado && <span className={styles.comparisonBadgeSelected}>selecionado</span>}
                  </td>
                  <td>{fmt(row.mse)}</td>
                  <td>{fmt(row.r2)}</td>
                  <td>{METODOS_BASELINE.has(row.metodo) ? "—" : fmtPercent(row.gain_vs_media_municipal)}</td>
                  <td className={styles.comparisonBandwidthCell}><BandwidthCell row={row} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
