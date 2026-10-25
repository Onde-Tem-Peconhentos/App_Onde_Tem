// src/components/ModelSummaryPanel.jsx
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

function fmt(v, digits = 3) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return Number(v).toFixed(digits);
}

function fmtPercent(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  return `${(Number(v) * 100).toFixed(1)}%`;
}

function TabelaResumo({ linhas }) {
  if (!linhas || linhas.length === 0) return <p className={styles.mapCaption}>Sem dados.</p>;
  return (
    <div style={{ overflowX: "auto" }}>
      <table className={styles.comparisonTable}>
        <thead>
          <tr>
            <th>Método</th>
            <th>R² médio</th>
            <th>Ganho médio vs. baseline</th>
            <th>RMSE médio</th>
            <th>MAE médio</th>
            <th>Vitórias</th>
          </tr>
        </thead>
        <tbody>
          {linhas.map((row, i) => (
            <tr key={row.metodo} className={i === 0 ? styles.comparisonRowBest : undefined}>
              <td>
                {METODO_LABELS[row.metodo] || row.metodo}
                {i === 0 && <span className={styles.comparisonBadgeBest}>melhor</span>}
              </td>
              <td>{fmt(row.r2_medio)}</td>
              <td>{fmtPercent(row.gain_medio)}</td>
              <td>{fmt(row.rmse_medio, 2)}</td>
              <td>{fmt(row.mae_medio, 2)}</td>
              <td>{row.vitorias} de {row.n}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/**
 * Painel colapsável com o desempenho médio de cada método, agregando TODOS
 * os animais e cadências — mostrado antes dos filtros de seleção da página,
 * escondido por padrão (o usuário abre quando quer ver "qual modelo é
 * melhor" de forma geral, antes de escolher um animal/cadência específico
 * nos filtros abaixo).
 */
export default function ModelSummaryPanel() {
  const [aberto, setAberto] = useState(false);
  const [dados, setDados] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cadenciaAtiva, setCadenciaAtiva] = useState(null);

  useEffect(() => {
    if (!aberto || dados || loading) return;
    setLoading(true);
    setError(null);
    fetch("http://localhost:8000/api/modelo/resumo")
      .then((r) => {
        if (!r.ok) throw new Error(`Erro HTTP ${r.status}`);
        return r.json();
      })
      .then((json) => {
        setDados(json);
        setLoading(false);
        const cadencias = Object.keys(json.por_cadencia || {});
        if (cadencias.length) setCadenciaAtiva(cadencias[0]);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [aberto, dados, loading]);

  return (
    <section className={styles.summaryPanel}>
      <button
        type="button"
        className={styles.summaryToggleButton}
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
      >
        <span className={styles.summaryToggleIcon}>{aberto ? "▾" : "▸"}</span>
        Desempenho médio dos modelos (todos os animais e cadências)
      </button>

      {aberto && (
        <div className={styles.summaryToggleContent}>
          {loading && <p className={styles.mapCaption}>Carregando resumo...</p>}
          {error && <p className={styles.mapCaption}>Não foi possível carregar o resumo: {error}</p>}

          {dados && (
            <>
              <p className={styles.mapCaption}>
                Média da linha mais recente de cada combinação (animal ×
                cadência × método). "Vitórias" = quantas vezes o método teve
                o menor MSE entre os 8 métodos, nessas combinações.
              </p>

              <h4 className={styles.categoryChartTitle}>Geral</h4>
              <TabelaResumo linhas={dados.geral} />

              {dados.por_cadencia && Object.keys(dados.por_cadencia).length > 0 && (
                <>
                  <h4 className={styles.categoryChartTitle} style={{ marginTop: 20 }}>Por cadência</h4>
                  <div className={styles.summaryTabs}>
                    {Object.keys(dados.por_cadencia).map((tp) => (
                      <button
                        key={tp}
                        type="button"
                        className={tp === cadenciaAtiva ? styles.summaryTabActive : styles.summaryTab}
                        onClick={() => setCadenciaAtiva(tp)}
                      >
                        {tp}
                      </button>
                    ))}
                  </div>
                  {cadenciaAtiva && <TabelaResumo linhas={dados.por_cadencia[cadenciaAtiva]} />}
                </>
              )}
            </>
          )}
        </div>
      )}
    </section>
  );
}
